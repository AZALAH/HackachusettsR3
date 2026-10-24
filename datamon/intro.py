"""Post-login loading screen (animated GIF) and a simple fade into the app.

Streamlit re-runs on every interaction, which restarts and visually freezes CSS
keyframe animations — so a scripted CSS loader never played. A GIF is an image
that plays itself, so it animates reliably here just as it would on a static
page. The loader GIF is pre-rendered and committed (see
``scripts/make_loader_gif.py``); the app only displays it.

The dashboard entry is a plain opacity fade — robust where a transform-based
"pop-in" was not.
"""

from __future__ import annotations

from pathlib import Path

LOADING_SECONDS = 9
LOADER_GIF = Path("assets/loader.gif")

FADE_CSS = """
<style>
section.main > div.block-container { animation: datamon-fade 0.8s ease both; }
@keyframes datamon-fade { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  section.main > div.block-container { animation: none; }
}
</style>
"""


def render_loading(st_module) -> None:
    """Show the animated GIF loader centered on the page."""
    st = st_module
    if LOADER_GIF.is_file():
        left, mid, right = st.columns([1, 2, 1])
        with mid:
            st.image(str(LOADER_GIF), use_container_width=True)
    else:  # asset missing — fall back to a plain spinner-style message
        st.info("Welcome to DataMon — starting the quality monitor…")


def render_fade(st_module) -> None:
    """Fade the dashboard in on the first render after the loader."""
    st_module.markdown(FADE_CSS, unsafe_allow_html=True)
