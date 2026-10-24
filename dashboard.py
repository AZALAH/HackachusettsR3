"""Streamlit operator portal for pre-training robot data quality control.

Run from the repository root with ``streamlit run dashboard.py``.
This is a trusted-file, local hackathon demo, not a hardened multi-user service.
"""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from datamon.auth import (
    LockoutState,
    session_expired,
    verify_password,
)
from datamon.branding import (
    inject_global_css,
    render_brand_header,
    render_login_hero,
)
from datamon.episode_quality import analyze_episodes
from datamon.frame_quality import DetectorConfig
from datamon.frames import DEFAULT_MAX_FILE_BYTES, load_parquet
from datamon.gate import GateConfig, IngestGate, OperatorAction
from datamon.help_agent import answer as help_answer
from datamon.help_agent import suggested_questions as help_suggested_questions
from datamon.intro import render_loading, render_reveal
from datamon.lerobot import load_episodes, task_map
from datamon.monitor import Monitor
from datamon.profiles import ProfileStore, RobotProfile
from datamon.stream import StreamIngestor
from datamon.tour import audio_path_for, render_tour

st.set_page_config(
    page_title="DataMon · Robot Data Quality Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css(st)


def _require_login() -> None:
    """Block the app behind a demo-grade login until authenticated."""
    state = st.session_state

    # Idle-timeout an existing session.
    if state.get("auth_user") and session_expired(state.get("auth_last_active")):
        for key in ("auth_user", "auth_role", "auth_last_active"):
            state.pop(key, None)
        state["auth_notice"] = "Session timed out. Please sign in again."

    if state.get("auth_user"):
        state["auth_last_active"] = time.time()
        return

    if "auth_lockout" not in state:
        state["auth_lockout"] = LockoutState()
    lockout: LockoutState = state["auth_lockout"]

    left, center, right = st.columns([1, 1.15, 1])
    with center:
        render_login_hero(st)
        notice = state.pop("auth_notice", None)
        if notice:
            st.warning(notice)
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if lockout.is_locked():
            st.error(
                f"Too many failed attempts. Try again in "
                f"{lockout.seconds_remaining()}s."
            )
        elif submitted:
            role = verify_password(username.strip(), password.strip())
            if role:
                lockout.record_success()
                state["auth_user"] = username.strip()
                state["auth_role"] = role
                state["auth_last_active"] = time.time()
                state["auth_just_logged_in"] = True
                state["reveal_token"] = uuid.uuid4().hex
                st.rerun()
            else:
                lockout.record_failure()
                st.error(
                    "Invalid username or password. Check for stray spaces; the "
                    "password is case-sensitive."
                )
        st.caption(
            "Demo-grade local login. Credentials for judges are in TESTING.md. "
            "Not production SSO — see SECURITY.md."
        )
    st.stop()


_require_login()

BRIDGE_ROOT = Path("data/lerobot/bridge_v2")
BRIDGE_DATA = BRIDGE_ROOT / "data" / "chunk-000"
DROID_ROOT = Path("data/lerobot/droid_100")
DROID_DATA = DROID_ROOT / "data" / "chunk-000" / "file-000.parquet"
INGEST_ROOT = Path("data/ingest_live")
PROFILE_STORE_PATH = Path("data/robot_profiles.json")
GRADE_COLOR = {"good": "#2e9e44", "review": "#d9a400", "reject": "#d64545"}


def _parse_ranges(text: str) -> dict[str, tuple[float, float]]:
    if not text.strip():
        return {}
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("channel ranges must be a JSON object")
    ranges = {}
    for channel, bounds in value.items():
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError(f"{channel} must map to [minimum, maximum]")
        ranges[str(channel)] = (float(bounds[0]), float(bounds[1]))
    return ranges


def play_error_cue() -> None:
    """Play the error alert sound once, if the audio file is present.

    Streamlit never re-plays an audio element it has already auto-played, and
    identical calls get the same element ID. A fresh ``alt`` per call makes
    every alert a new element, so the second rejection beeps too.
    """
    path = audio_path_for("alert_error")
    if path is not None:
        st.audio(
            str(path),
            format="audio/mpeg" if path.suffix == ".mp3" else "audio/wav",
            autoplay=True,
            alt=f"Alert sound ({uuid.uuid4().hex[:8]})",
        )


@st.cache_resource(show_spinner=False)
def ensure_demo_data() -> bool:
    """Download the bounded demo dataset once if it is missing.

    On a hosted deploy (e.g. Streamlit Community Cloud) the one-time
    ``download_frames`` script is never run, so the data directory is empty. This
    fetches the same pinned, checksum-verified slice on first load. Cached so it
    runs at most once per server process.
    """
    marker = Path("data/lerobot/droid_100/data/chunk-000/file-000.parquet")
    if marker.is_file():
        return True
    try:
        from scripts.download_frames import main as download_main

        with st.spinner("Preparing the demo dataset (one-time, ~7 MB)…"):
            download_main()
        return True
    except Exception as error:  # surfaced to the user, not a hard crash
        st.warning(
            "Could not fetch the demo dataset automatically. Run "
            "`python scripts/download_frames.py` locally. "
            f"Details: {error}"
        )
        return False


@st.cache_resource(show_spinner=False)
def load_monitor(
    source: str,
    fps: float,
    jitter_tolerance: float,
    reject_below: float,
    accept_at: float,
    ranges_json: str,
    static_channels_csv: str,
) -> Monitor:
    ranges = _parse_ranges(ranges_json)
    static_channels = frozenset(
        value.strip() for value in static_channels_csv.split(",") if value.strip()
    )
    detector = DetectorConfig(
        jitter_tolerance=jitter_tolerance,
        cadence_tolerance=jitter_tolerance,
        ranges=ranges,
        allowed_static_channels=static_channels,
    )
    if source == "DROID-100":
        metadata = load_episodes(DROID_ROOT)
        monitor = Monitor.from_parquet(
            DROID_DATA,
            fps=fps,
            tasks_by_episode=task_map(metadata),
            source="droid_100",
            detector_config=detector,
            accept_at=accept_at,
            reject_below=reject_below,
        )
    else:
        metadata = load_episodes(BRIDGE_ROOT)
        files = sorted(BRIDGE_DATA.glob("episode_*.parquet"))
        monitor = Monitor.from_episode_files(
            files,
            fps=fps,
            tasks_by_episode=task_map(metadata),
            source="bridge_v2",
            detector_config=detector,
            accept_at=accept_at,
            reject_below=reject_below,
        )
    return monitor.fit()


@st.cache_data(show_spinner=False)
def analyze_bridge_metadata() -> tuple[pd.DataFrame, object]:
    metadata = load_episodes(BRIDGE_ROOT)
    return metadata, analyze_episodes(metadata)


def _gate_config(monitor: Monitor, reject_below: float, accept_at: float) -> GateConfig:
    return GateConfig(
        accept_at=float(accept_at),
        reject_below=float(reject_below),
        detector=monitor.detector_config,
        require_task=True,
    )


@st.cache_resource(show_spinner=False)
def reference_anomaly_model(
    source: str,
    fps: float,
    jitter_tolerance: float,
    reject_below: float,
    accept_at: float,
    ranges_json: str,
    static_channels_csv: str,
):
    """Fit the gate's anomaly baseline once per settings, shared by all sessions.

    Calibration re-checks every reference episode, which was the slowest step of
    a fresh session. The fitted model is read-only at scoring time, so each
    session's gate can reuse it while keeping its own storage directory.
    """
    monitor = load_monitor(
        source, fps, jitter_tolerance, reject_below, accept_at,
        ranges_json, static_channels_csv,
    )
    scratch = Path(tempfile.mkdtemp(prefix="datamon-calibrate-"))
    gate = IngestGate(scratch, _gate_config(monitor, reject_below, accept_at))
    return gate.calibrate(monitor.episodes).anomaly_model


# The sidebar's default settings. The loader warms exactly these so the first
# dashboard render after sign-in is served from cache.
DEFAULT_SETTINGS = ("DROID-100", 15.0, 0.25, 55.0, 80.0, "", "")


def _warm_caches() -> None:
    """Load and calibrate the default view while the loading screen plays."""
    if not ensure_demo_data():
        return
    monitor = load_monitor(*DEFAULT_SETTINGS)
    monitor.summary_table()  # scores every episode once; results are memoized
    reference_anomaly_model(*DEFAULT_SETTINGS)
    analyze_bridge_metadata()


def _play_intro() -> None:
    """Full-screen GIF loader once, right after a fresh sign-in."""
    if not st.session_state.pop("auth_just_logged_in", False):
        return
    render_loading(st, warmup=_warm_caches)  # owns the screen, then fades out
    st.session_state["auth_show_reveal"] = True
    st.rerun()              # next run renders the real app and pops it in


_play_intro()

# On the run after the loader, every tile pops into place once.
if st.session_state.pop("auth_show_reveal", False):
    render_reveal(st, st.session_state.get("reveal_token", "reveal"))


st.sidebar.title("Monitor setup")
st.sidebar.caption("Configure the source and quality policy before collection.")

with st.sidebar.container(border=True):
    st.markdown(
        f"Signed in as **{st.session_state.get('auth_user', '?')}** "
        f"(`{st.session_state.get('auth_role', '?')}`)"
    )
    if st.button("Sign out", key="sign_out", width="stretch"):
        for key in ("auth_user", "auth_role", "auth_last_active"):
            st.session_state.pop(key, None)
        st.rerun()

@st.fragment
def _tour_panel() -> None:
    """Tour controls re-run only this panel, not the whole dashboard."""
    st.caption("New here? Take the narrated, arrow-guided walkthrough.")
    reduced_motion = st.checkbox(
        "Reduce motion", value=False, key="tour_reduced_motion",
        help="Turn off the bouncing arrow animation in the tour.",
    )
    render_tour(st, reduced_motion=reduced_motion)


with st.sidebar.container(border=True):
    _tour_panel()

source = st.sidebar.selectbox("Data source", ["DROID-100", "BridgeData V2 (sample)"])
default_fps = 15.0 if source == "DROID-100" else 5.0

profile_store = ProfileStore(PROFILE_STORE_PATH)
with st.sidebar.expander("Robot profile"):
    st.caption(
        "Save a rig's expected rate, channel ranges, and static channels as a "
        "named profile, then reapply it in one click for the next collection."
    )
    saved_names = profile_store.names()
    chosen = st.selectbox(
        "Saved profiles", ["(none)"] + saved_names, key="profile_choice",
    )
    if chosen != "(none)" and st.button("Apply profile", width="stretch"):
        profile = profile_store.get(chosen)
        st.session_state["fps_input"] = float(profile.fps)
        st.session_state["ranges_json_input"] = json.dumps(
            {name: list(bounds) for name, bounds in profile.ranges.items()}
        ) if profile.ranges else ""
        st.session_state["static_channels_input"] = ", ".join(
            profile.allowed_static_channels
        )
        st.session_state["jitter_pct_input"] = int(round(profile.jitter_tolerance * 100))
        st.session_state["profile_flash"] = f"Applied profile '{chosen}'."
        st.rerun()
    new_name = st.text_input(
        "Save current settings as", placeholder="franka_panda", key="profile_new_name",
    )
    if st.button("Save profile", width="stretch"):
        try:
            profile = RobotProfile(
                name=new_name.strip(),
                fps=float(st.session_state.get("fps_input", default_fps)),
                jitter_tolerance=st.session_state.get("jitter_pct_input", 25) / 100.0,
                cadence_tolerance=st.session_state.get("jitter_pct_input", 25) / 100.0,
                ranges=_parse_ranges(st.session_state.get("ranges_json_input", "")),
                allowed_static_channels=[
                    value.strip()
                    for value in st.session_state.get("static_channels_input", "").split(",")
                    if value.strip()
                ],
                task_family=(source.split()[0].lower()),
            )
            profile_store.save(profile)
            st.session_state["profile_flash"] = f"Saved profile '{profile.name}'."
            st.rerun()
        except Exception as error:
            st.error(f"Could not save the profile: {error}")
    flash = st.session_state.pop("profile_flash", None)
    if flash:
        st.success(flash)

fps = st.sidebar.number_input(
    "Expected capture rate (fps)", 1.0, 120.0,
    float(st.session_state.get("fps_input", default_fps)), 1.0, key="fps_input",
)
reject_below, accept_at = st.sidebar.slider(
    "Quality bands (reject / accept)", 0, 100, (55, 80),
    help="Below the first value is rejected; at or above the second is accepted.",
)
jitter_tolerance = st.sidebar.slider(
    "Timing tolerance (%)", 5, 100,
    int(st.session_state.get("jitter_pct_input", 25)), key="jitter_pct_input",
) / 100.0
play_speed = st.sidebar.slider("Playback speed", 0.25, 8.0, 2.0, 0.25)

with st.sidebar.expander("Advanced channel rules"):
    ranges_json = st.text_area(
        "Channel ranges (JSON)",
        value=st.session_state.get("ranges_json_input", ""),
        placeholder='{"state_0": [-1.0, 1.0], "action_0": [-1.0, 1.0]}',
        help="Optional per-channel hard bounds. Non-finite values are always rejected.",
        key="ranges_json_input",
    )
    static_channels_csv = st.text_input(
        "Allowed static channels",
        value=st.session_state.get("static_channels_input", ""),
        placeholder="state_6, action_6",
        help="Comma-separated channels that are expected to stay constant.",
        key="static_channels_input",
    )

ensure_demo_data()
try:
    monitor = load_monitor(
        source, float(fps), jitter_tolerance, float(reject_below),
        float(accept_at), ranges_json, static_channels_csv,
    )
except Exception as error:
    st.error(f"Could not load the demo data: {error}")
    st.code("python scripts/download_frames.py")
    st.stop()

episode_indices = [episode.episode_index for episode in monitor.episodes]
st.sidebar.metric("Episodes loaded", len(episode_indices))

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
signature = (
    source, float(fps), jitter_tolerance, float(reject_below), float(accept_at),
    ranges_json, static_channels_csv,
)
if st.session_state.get("gate_signature") != signature:
    session_root = INGEST_ROOT / st.session_state.session_id / source.lower().replace(" ", "-")
    st.session_state.gate = IngestGate(
        session_root,
        _gate_config(monitor, reject_below, accept_at),
        anomaly_model=reference_anomaly_model(*signature),
    )
    st.session_state.gate_signature = signature
gate: IngestGate = st.session_state.gate

render_brand_header(st, clock=True)
st.title("Robot Data-Collection Quality Monitor")
st.caption(
    "Catch sensor, timing, labeling, and demonstration problems before they "
    "enter a training pipeline."
)

tab_ingest, tab_review, tab_live, tab_dataset, tab_labels = st.tabs([
    "Ingest gate", "Review queue", "Episode playback", "Dataset quality",
    "Label / coverage",
])

with tab_ingest:
    st.subheader("Gate incoming data before training")
    st.caption(
        "Accepted episodes enter the clean staging store. Review episodes are held "
        "for an operator. Integrity failures are quarantined."
    )
    upload_column, stream_column = st.columns(2)

    with upload_column:
        st.markdown(
            "**Upload a robot recording**",
            help=(
                "A .parquet file in the LeRobot format: Hugging Face's open "
                "standard for robot datasets. Each row is one moment of the "
                "recording (the robot's joint readings and the command it was "
                "given), plus a timestamp."
            ),
        )
        st.caption("LeRobot .parquet format, the open standard for robot datasets.")
        task_description = st.text_input(
            "Task description",
            placeholder="Put the marker in the pot",
            help="Used when the parquet does not contain a task description.",
        )
        uploaded = st.file_uploader(
            "Episode parquet", type=["parquet"], label_visibility="collapsed",
        )
        if uploaded is not None:
            if uploaded.size > DEFAULT_MAX_FILE_BYTES:
                st.error(
                    f"Upload is {uploaded.size / 1e6:.1f} MB; the demo limit is "
                    f"{DEFAULT_MAX_FILE_BYTES / 1e6:.0f} MB."
                )
            else:
                temporary_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as handle:
                        handle.write(uploaded.getbuffer())
                        temporary_path = Path(handle.name)
                    episodes = load_parquet(
                        temporary_path,
                        fps=float(fps),
                        source=f"upload-{Path(uploaded.name).stem}",
                    )
                    for episode in episodes:
                        if task_description.strip():
                            episode.task = task_description.strip()
                        preview = gate.evaluate(episode)
                        color_key = {
                            "accept": "good", "review": "review", "reject": "reject",
                        }[preview.decision.value]
                        st.markdown(
                            f"Episode {episode.episode_index}: "
                            f"<span style='color:{GRADE_COLOR[color_key]};font-weight:700'>"
                            f"{preview.decision.value.upper()}</span> "
                            f"({preview.score.score:.0f}/100)",
                            unsafe_allow_html=True,
                        )
                        for reason in preview.reasons[:4]:
                            st.caption(f"• {reason}")
                        if st.button(
                            f"Process episode {episode.episode_index}",
                            key=f"admit-{uploaded.name}-{episode.episode_index}",
                        ):
                            admitted = gate.admit(episode)
                            st.success(
                                f"{admitted.decision.value.upper()}: exact evaluated "
                                f"episode stored at {admitted.stored_path}"
                            )
                            if admitted.decision.value == "reject":
                                play_error_cue()
                except Exception as error:
                    st.error(f"The parquet did not pass schema validation: {error}")
                    play_error_cue()
                finally:
                    if temporary_path:
                        temporary_path.unlink(missing_ok=True)

    with stream_column:
        st.markdown("**Replay a loaded episode through the live stream API**")
        stream_index = st.selectbox("Episode to replay", episode_indices, key="stream-episode")
        if st.button("Stream and gate ▶", width="stretch"):
            warning_log = []
            progress = st.progress(0.0)
            status = st.empty()
            ingestor = StreamIngestor(
                gate,
                fps=float(fps),
                on_frame=lambda feedback: warning_log.extend(
                    (feedback.frame_index, warning) for warning in feedback.warnings
                ),
            )
            episode = monitor.get_episode(stream_index)
            for position in range(episode.n_frames):
                ingestor.push_frame(
                    episode.episode_index,
                    int(episode.frame_index[position]),
                    float(episode.timestamp[position]),
                    episode.state[position],
                    episode.action[position],
                    task=episode.task,
                    task_index=episode.task_index,
                    source=episode.source,
                )
                progress.progress((position + 1) / episode.n_frames)
                status.markdown(
                    f"Frame {position + 1}/{episode.n_frames} · "
                    f"{len(warning_log)} live warning(s)"
                )
                time.sleep(max(0.0, 1.0 / (fps * play_speed)))
            admitted = ingestor.end_episode()
            progress.empty()
            assert admitted is not None
            color_key = {
                "accept": "good", "review": "review", "reject": "reject",
            }[admitted.decision.value]
            st.markdown(
                f"### Gate decision: <span style='color:{GRADE_COLOR[color_key]}'>"
                f"{admitted.decision.value.upper()}</span> "
                f"({admitted.score.score:.0f}/100)",
                unsafe_allow_html=True,
            )
            if admitted.decision.value == "reject":
                play_error_cue()
            for frame_index, warning in warning_log[:5]:
                st.caption(f"frame {frame_index}: {warning}")

    st.divider()
    stats = gate.stats()
    metrics = st.columns(4)
    metrics[0].metric("Accepted", stats["accept"])
    metrics[1].metric("Review", stats["review"])
    metrics[2].metric("Rejected", stats["reject"])
    metrics[3].metric("Rejected frames", gate.wasted_frames_prevented())

with tab_review:
    st.subheader("Operator review queue")
    st.caption(
        "Episodes the gate could not accept or reject on its own. Promote a good "
        "demonstration to clean, reject a bad one, or request recollection. Every "
        "decision is appended to the audit manifest; the content ID and prior "
        "history are preserved."
    )
    queue = gate.review_queue()
    if not queue:
        st.success("The review queue is empty. Nothing is waiting on an operator.")
    else:
        st.metric("Awaiting review", len(queue))
        for record in queue:
            ingest_id = record.get("ingest_id", "")
            short_id = ingest_id[:12]
            episode_index = record.get("episode_index")
            score = record.get("score", 0.0)
            with st.container(border=True):
                header = st.columns([3, 1])
                header[0].markdown(
                    f"**Episode {episode_index}** · source `{record.get('source')}` "
                    f"· content `{short_id}`"
                )
                header[1].markdown(
                    f"<div style='text-align:right;color:{GRADE_COLOR['review']};"
                    f"font-weight:700;font-size:1.3rem'>{score:.0f}/100</div>",
                    unsafe_allow_html=True,
                )
                for reason in (record.get("reasons") or [])[:4]:
                    st.caption(f"• {reason}")

                note = st.text_input(
                    "Decision note (optional)",
                    key=f"review-note-{ingest_id}",
                    placeholder="Why are you promoting, rejecting, or recollecting?",
                )
                actions = st.columns(3)

                def _apply(
                    action: OperatorAction,
                    ingest_id=ingest_id,
                    note=note,
                    short_id=short_id,
                ):
                    try:
                        outcome = gate.operator_decision(ingest_id, action, note)
                    except Exception as error:  # surfaced inline, queue stays usable
                        st.error(f"Could not apply the decision: {error}")
                        play_error_cue()
                        return
                    st.session_state["review_flash"] = (
                        f"{action.value.replace('operator_', '').upper()} applied to "
                        f"episode {outcome.episode_index} "
                        f"→ {outcome.decision.value.upper()} ({short_id})"
                    )
                    st.rerun()

                if actions[0].button(
                    "Promote to clean ✅", key=f"promote-{ingest_id}",
                    width="stretch",
                ):
                    _apply(OperatorAction.PROMOTE)
                if actions[1].button(
                    "Reject ⛔", key=f"reject-{ingest_id}", width="stretch",
                ):
                    _apply(OperatorAction.REJECT)
                if actions[2].button(
                    "Request recollection 🔁", key=f"recollect-{ingest_id}",
                    width="stretch",
                ):
                    _apply(OperatorAction.RECOLLECT)

                with st.expander("Audit history"):
                    for event in gate.history(ingest_id):
                        stamp = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(event.get("ts", 0))
                        )
                        label = event.get("action", "automated").replace(
                            "operator_", ""
                        )
                        line = (
                            f"{stamp} · {label} → "
                            f"{event.get('decision', '?').upper()}"
                        )
                        if event.get("note"):
                            line += f" · {event['note']}"
                        st.caption(line)

    flash = st.session_state.pop("review_flash", None)
    if flash:
        st.toast(flash)

with tab_live:
    selection, play_column = st.columns([3, 1])
    episode_index = selection.selectbox("Episode", episode_indices, key="playback-episode")
    play = play_column.button("Play ▶", width="stretch")
    result = monitor.analyze_episode(episode_index)
    score = result.score

    summary = st.columns(4)
    color = GRADE_COLOR[score.grade]
    summary[0].markdown(
        f"### Quality\n<span style='color:{color};font-size:2rem;font-weight:700'>"
        f"{score.score:.0f}/100</span>", unsafe_allow_html=True,
    )
    summary[1].markdown(
        f"### Verdict\n<span style='color:{color};font-size:1.6rem;font-weight:700'>"
        f"{score.grade.upper()}</span>", unsafe_allow_html=True,
    )
    summary[2].metric("Frames", result.episode.n_frames)
    summary[3].metric(
        "Anomaly",
        "N/A" if score.anomaly_score is None else f"{score.anomaly_score:.2f}",
    )
    flags = [
        *result.episode_flags,
        *result.frame_report.flags,
    ]
    actionable = [flag for flag in flags if flag.severity.value != "info"]
    if actionable:
        st.subheader(f"Flags ({len(actionable)})")
        for flag in actionable[:12]:
            icon = "🔴" if flag.severity.value == "error" else "🟠"
            st.write(f"{icon} **{flag.check}** — {flag.reason}")
    else:
        st.success("No actionable quality issues detected.")

    names = result.episode.channel_names()
    state_columns = [name for name in names if name.startswith("state")]
    if play:
        rows = []
        chart = st.empty()
        readout = st.empty()
        progress = st.progress(0.0)
        for position, frame in enumerate(monitor.stream_episode(episode_index)):
            rows.append(np.concatenate([frame["state"], frame["action"]]))
            interval = "" if frame["interval"] is None else f"{frame['interval'] * 1000:.0f} ms"
            readout.markdown(
                f"**Frame {frame['frame']}** · t={frame['timestamp']:.2f}s · "
                f"interval {'🟢' if frame['interval_ok'] else '🔴'} {interval}"
            )
            chart.line_chart(pd.DataFrame(rows, columns=names)[state_columns], height=260)
            progress.progress((position + 1) / result.episode.n_frames)
            time.sleep(max(0.0, 1.0 / (fps * play_speed)))
        progress.empty()
    else:
        data = pd.DataFrame(result.episode.channels, columns=names)
        st.line_chart(data[state_columns], height=260)
        st.caption("State channels (proprioception). Press Play for timed replay.")

with tab_dataset:
    st.subheader("Episode quality across the loaded dataset")
    table = monitor.summary_table()
    counts = monitor.grade_counts()
    metrics = st.columns(3)
    metrics[0].metric("Good", counts["good"])
    metrics[1].metric("Review", counts["review"])
    metrics[2].metric("Reject", counts["reject"])
    st.bar_chart(table.set_index("episode")["score"], height=240)
    st.dataframe(
        table.style.apply(
            lambda row: [f"background-color: {GRADE_COLOR[row['grade']]}22"] * len(row),
            axis=1,
        ),
        width="stretch",
        height=360,
    )
    worst = table.iloc[0]
    st.info(
        f"Lowest-scoring episode: #{int(worst['episode'])} at "
        f"{worst['score']:.0f}/100. Review or recollect before training."
    )

with tab_labels:
    st.subheader("BridgeData V2 label quality and coverage")
    try:
        metadata, report = analyze_bridge_metadata()
    except Exception as error:
        st.warning(f"BridgeData metadata unavailable: {error}")
        st.code("python scripts/download_frames.py")
    else:
        coverage = report.coverage
        metrics = st.columns(4)
        metrics[0].metric("Episodes", f"{report.n_episodes:,}")
        metrics[1].metric("Missing labels", f"{coverage['missing_label_rate'] * 100:.1f}%")
        metrics[2].metric("Unique task strings", f"{coverage['unique_tasks']:,}")
        metrics[3].metric("Singleton task strings", f"{coverage['singleton_tasks']:,}")
        st.caption(
            "Singleton strings are a coverage lead, not proof of a semantic gap; "
            "task wording should be normalized before collection planning."
        )
        st.write("**Flags by type:**", report.counts_by_check())
        flags = report.flags_frame()
        if not flags.empty:
            st.dataframe(flags.head(200), width="stretch", height=360)

# --- Grounded help agent (bottom-right) ------------------------------------

st.markdown(
    """
    <style>
    div[data-testid="stExpander"]:has(#datamon-help-anchor) {
        position: fixed; bottom: 1rem; right: 1rem; width: 360px;
        max-width: 90vw; z-index: 1000;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35); border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
@st.fragment
def _help_panel() -> None:
    """Asking a question re-runs only this panel, not the whole dashboard."""
    with st.expander("💬 Ask about the interface", expanded=False):
        st.markdown("<span id='datamon-help-anchor'></span>", unsafe_allow_html=True)
        st.caption(
            "A grounded assistant — it answers only from DataMon's own "
            "documentation, so it never guesses."
        )
        picked = st.selectbox(
            "Common questions", ["(choose a question)"] + help_suggested_questions(),
            key="help_pick",
        )
        typed = st.text_input(
            "…or ask your own", key="help_typed",
            placeholder="e.g. how does the gate decide?",
        )
        query = typed.strip() or (picked if picked != "(choose a question)" else "")
        if query:
            st.info(help_answer(query))


_help_panel()
