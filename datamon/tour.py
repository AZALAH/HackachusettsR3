"""Accessible guided tour overlay for the operator dashboard.

A game-style step-by-step walkthrough: each step highlights one area of the UI,
points an arrow toward it, shows a short caption, and plays optional narration
audio. Every step is usable three ways at once -- read the caption, hear the
narration, or follow the arrow -- so the tour never depends on a single sense.

Narration audio is supplied by the user (see ``narration/SCRIPT.md``). A step
whose audio file is absent simply plays no sound; the caption still shows. Motion
respects the viewer's reduced-motion preference and a tour-level toggle.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

AUDIO_DIR = Path("narration/audio")
# An mp3 (recorded narration) wins over a wav (generated cue) when both exist.
_AUDIO_SUFFIXES = (".mp3", ".wav")


@dataclass(frozen=True)
class TourStep:
    step_id: str          # matches narration/audio/<step_id>.<ext>
    title: str
    caption: str
    target: str           # where to look, in plain words
    arrow: str            # a direction glyph pointing at the target


TOUR_STEPS: List[TourStep] = [
    TourStep("step_01_welcome", "Welcome to DataMon",
             "A robot only learns from what you feed it, and one bad "
             "demonstration can quietly teach it the wrong move. DataMon catches "
             "bad data before training does.",
             "the whole screen", "\u25ce"),
    TourStep("step_02_sidebar_setup", "Setup panel",
             "On the left you pick the data source and set how strict the checks "
             "are, before a single recording rolls in.",
             "the sidebar on the left", "\u25c0"),
    TourStep("step_03_robot_profile", "Robot profile",
             "Every robot is different. Save one as a profile -- its speed, its "
             "limits -- and load it back in a single click.",
             "the 'Robot profile' expander in the sidebar", "\u25c0"),
    TourStep("step_04_quality_bands", "Quality bands",
             "These are the pass marks. Below the first line, rejected; above the "
             "second, accepted; in between, a human takes a look.",
             "the 'Quality bands' slider in the sidebar", "\u25c0"),
    TourStep("step_05_ingest_gate", "The ingest gate",
             "Every recording is scored and sorted here: clean, held for review, "
             "or quarantined, before it can poison a training run.",
             "the 'Ingest gate' tab", "\u25b2"),
    TourStep("step_06_upload_and_stream", "Upload or replay",
             "Upload a finished recording, or replay a live one frame by frame. "
             "Same checks either way.",
             "the upload and stream panels", "\u25b2"),
    TourStep("step_07_review_queue", "The review queue",
             "When DataMon isn't sure, it asks you: promote a good recording, "
             "reject a bad one, or send it back to be recorded again.",
             "the 'Review queue' tab", "\u25b2"),
    TourStep("step_08_audit_history", "Audit history",
             "Every decision is written down -- who chose what, and when. Nothing "
             "is ever quietly overwritten.",
             "the 'Audit history' expander on a review item", "\u25b2"),
    TourStep("step_09_dataset_quality", "The report card",
             "Built on real public robot datasets -- DROID and BridgeData. One row "
             "per recording, each with a score, a verdict, and its reasons.",
             "the 'Dataset quality' tab", "\u25b2"),
    TourStep("step_10_labels_coverage", "Labels and coverage",
             "This flags recordings the robot was never properly told the point "
             "of -- missing or nonsense task descriptions.",
             "the 'Label / coverage' tab", "\u25b2"),
    TourStep("step_11_closing", "That's DataMon",
             "Good data in, bad data out, caught early. Built with Kiro -- specs, "
             "agent hooks, and property-based tests doing the heavy lifting.",
             "you're all set", "\u25ce"),
]


def audio_path_for(step_id: str) -> Optional[Path]:
    """Return the best existing audio file for a step, or None."""
    for suffix in _AUDIO_SUFFIXES:
        candidate = AUDIO_DIR / f"{step_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def go_to_step(state, index: int) -> None:
    """Move the tour to ``index`` (clamped) and count a new visit.

    Used as a button callback, so the state changes BEFORE the re-run and one
    click costs one re-run. The visit counter gives each visit's narration a
    distinct identity, so Back replays a line instead of staying silent.
    """
    state["tour_active"] = True
    state["tour_index"] = max(0, min(int(index), len(TOUR_STEPS) - 1))
    state["tour_visit"] = int(state.get("tour_visit", 0)) + 1


def end_tour(state) -> None:
    state["tour_active"] = False


def render_tour(st_module, *, reduced_motion: bool = False) -> None:
    """Render the tour launcher and, when active, the current step's card.

    Narration auto-plays on each step through Streamlit's own media server (the
    player is hidden by the global CSS); a bold arrow points in the step's
    direction. ``st_module`` is the imported ``streamlit`` module, passed in so
    this stays unit-testable without a running Streamlit server.
    """
    st = st_module
    state = st.session_state

    if not state.get("tour_active"):
        st.button(
            "\u25b6 Start guided tour", key="tour_start",
            on_click=go_to_step, args=(state, 0),
        )
        return

    index = int(state.get("tour_index", 0))
    index = max(0, min(index, len(TOUR_STEPS) - 1))
    step = TOUR_STEPS[index]
    animate = not reduced_motion

    # A bold arrow that points in the step's direction and nudges toward it.
    nudge = {
        "\u25c0": "datamon-nudge-x-rev", "\u25b2": "datamon-nudge-y-rev",
        "\u25b6": "datamon-nudge-x", "\u25ce": "datamon-spin",
    }.get(step.arrow, "datamon-nudge-y")
    arrow_anim = f"animation:{nudge} 1s ease-in-out infinite;" if animate else ""
    card = f"""
    <style>
    @keyframes datamon-nudge-y {{
      0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(7px)}} }}
    @keyframes datamon-nudge-y-rev {{
      0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-7px)}} }}
    @keyframes datamon-nudge-x-rev {{
      0%,100%{{transform:translateX(0)}} 50%{{transform:translateX(-7px)}} }}
    @keyframes datamon-nudge-x {{
      0%,100%{{transform:translateX(0)}} 50%{{transform:translateX(7px)}} }}
    @keyframes datamon-spin {{ from{{transform:rotate(0)}} to{{transform:rotate(360deg)}} }}
    @media (prefers-reduced-motion: reduce) {{
      .datamon-arrow {{ animation:none !important; }} }}
    </style>
    <div style="border:2px solid #2dd4bf;border-radius:12px;
                padding:1rem 1.2rem;background:rgba(45,212,191,0.10);color:inherit;">
      <div style="display:flex;align-items:center;gap:0.7rem;">
        <span class="datamon-arrow" style="display:inline-block;font-size:2.4rem;
              color:#2dd4bf;{arrow_anim}">{step.arrow}</span>
        <strong style="font-size:1.1rem;">Step {index + 1} of {len(TOUR_STEPS)}
          &mdash; {step.title}</strong>
      </div>
      <p style="margin:0.5rem 0 0.3rem;">{step.caption}</p>
      <p style="margin:0;opacity:0.75;font-size:0.9rem;">
        \U0001f449 Look at: <em>{step.target}</em></p>
    </div>
    """
    st.markdown(card, unsafe_allow_html=True)

    # Auto-play the step's narration. Streamlit serves the file by URL (no
    # base64 blob re-sent on every click) and never replays an element it has
    # already played, so ``alt`` carries the visit number to make each visit a
    # new element. A browser that blocks autoplay stays silent; the caption
    # above carries the same words.
    audio = audio_path_for(step.step_id)
    if audio is not None:
        st.audio(
            str(audio),
            format="audio/mpeg" if audio.suffix == ".mp3" else "audio/wav",
            autoplay=True,
            alt=f"Narration: {step.title} (visit {state.get('tour_visit', 0)})",
        )

    controls = st.columns([1, 1, 1])
    controls[0].button(
        "\u25c0 Back", key="tour_back", disabled=index == 0,
        on_click=go_to_step, args=(state, index - 1),
    )
    if index < len(TOUR_STEPS) - 1:
        controls[1].button(
            "Next \u25b6", key="tour_next",
            on_click=go_to_step, args=(state, index + 1),
        )
    else:
        controls[1].button(
            "Finish \u2713", key="tour_finish", on_click=end_tour, args=(state,),
        )
    controls[2].button("Exit tour", key="tour_exit", on_click=end_tour, args=(state,))
