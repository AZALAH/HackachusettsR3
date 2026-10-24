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

from datamon.episode_quality import analyze_episodes
from datamon.frame_quality import DetectorConfig
from datamon.frames import DEFAULT_MAX_FILE_BYTES, load_parquet
from datamon.gate import GateConfig, IngestGate
from datamon.lerobot import load_episodes, task_map
from datamon.monitor import Monitor
from datamon.stream import StreamIngestor

st.set_page_config(page_title="Robot Data Quality Monitor", layout="wide")

BRIDGE_ROOT = Path("data/lerobot/bridge_v2")
BRIDGE_DATA = BRIDGE_ROOT / "data" / "chunk-000"
DROID_ROOT = Path("data/lerobot/droid_100")
DROID_DATA = DROID_ROOT / "data" / "chunk-000" / "file-000.parquet"
INGEST_ROOT = Path("data/ingest_live")
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


@st.cache_data
def load_metadata(root: str) -> pd.DataFrame:
    return load_episodes(Path(root))


@st.cache_resource
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


@st.cache_data
def analyze_bridge_metadata() -> tuple[pd.DataFrame, object]:
    metadata = load_episodes(BRIDGE_ROOT)
    return metadata, analyze_episodes(metadata)


st.sidebar.title("Monitor setup")
st.sidebar.caption("Configure the source and quality policy before collection.")
source = st.sidebar.selectbox("Data source", ["DROID-100", "BridgeData V2 (sample)"])
default_fps = 15.0 if source == "DROID-100" else 5.0
fps = st.sidebar.number_input("Expected capture rate (fps)", 1.0, 120.0, default_fps, 1.0)
reject_below, accept_at = st.sidebar.slider(
    "Quality bands (reject / accept)", 0, 100, (55, 80),
    help="Below the first value is rejected; at or above the second is accepted.",
)
jitter_tolerance = st.sidebar.slider("Timing tolerance (%)", 5, 100, 25) / 100.0
play_speed = st.sidebar.slider("Playback speed", 0.25, 8.0, 2.0, 0.25)

with st.sidebar.expander("Advanced channel rules"):
    ranges_json = st.text_area(
        "Channel ranges (JSON)",
        value="",
        placeholder='{"state_0": [-1.0, 1.0], "action_0": [-1.0, 1.0]}',
        help="Optional per-channel hard bounds. Non-finite values are always rejected.",
    )
    static_channels_csv = st.text_input(
        "Allowed static channels",
        value="",
        placeholder="state_6, action_6",
        help="Comma-separated channels that are expected to stay constant.",
    )

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
    gate_config = GateConfig(
        accept_at=float(accept_at),
        reject_below=float(reject_below),
        detector=monitor.detector_config,
        require_task=True,
    )
    session_root = INGEST_ROOT / st.session_state.session_id / source.lower().replace(" ", "-")
    st.session_state.gate = IngestGate(session_root, gate_config).calibrate(monitor.episodes)
    st.session_state.gate_signature = signature
gate: IngestGate = st.session_state.gate

st.title("Robot Data-Collection Quality Monitor")
st.caption(
    "Catch sensor, timing, labeling, and demonstration problems before they "
    "enter a training pipeline."
)
st.info(
    "Local trusted-file demo: uploads are processed in this session and routed "
    "under data/ingest_live/. Do not expose this app publicly without authentication."
)

tab_ingest, tab_live, tab_dataset, tab_labels = st.tabs([
    "Ingest gate", "Episode playback", "Dataset quality", "Label / coverage",
])

with tab_ingest:
    st.subheader("Gate incoming data before training")
    st.caption(
        "Accepted episodes enter the clean staging store. Review episodes are held "
        "for an operator. Integrity failures are quarantined."
    )
    upload_column, stream_column = st.columns(2)

    with upload_column:
        st.markdown("**Upload LeRobot frame parquet**")
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
                except Exception as error:
                    st.error(f"The parquet did not pass schema validation: {error}")
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
            for frame_index, warning in warning_log[:5]:
                st.caption(f"frame {frame_index}: {warning}")

    st.divider()
    stats = gate.stats()
    metrics = st.columns(4)
    metrics[0].metric("Accepted", stats["accept"])
    metrics[1].metric("Review", stats["review"])
    metrics[2].metric("Rejected", stats["reject"])
    metrics[3].metric("Rejected frames", gate.wasted_frames_prevented())

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
