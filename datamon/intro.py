"""Post-login loading screen (animated GIF) and a smooth fade into the app.

Streamlit re-runs on every interaction, which restarts and freezes CSS keyframe
animations. A GIF plays itself, so it animates reliably. The loader GIF is
pre-rendered and committed (see ``scripts/make_loader_gif.py``); the app only
displays it.

While the loader is up it OWNS the screen: Streamlit's header, the image
fullscreen button, and any other chrome are hidden so nothing else shows behind
or above it. The dashboard then fades in once, smoothly.
"""

from __future__ import annotations

from pathlib import Path

LOADING_SECONDS = 9
LOADER_GIF = Path("assets/loader.gif")

# Hides all Streamlit chrome and centers the loader as a full-screen takeover.
_LOADER_CSS = """
<style>
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stSidebar"] { display: none !important; }
/* Hide the image fullscreen/expand button on the loader image. */
[data-testid="StyledFullScreenButton"],
button[title="View fullscreen"] { display: none !important; }
[data-testid="stAppViewContainer"] {
  background: radial-gradient(1200px 600px at 50% 40%, #13303a 0%, #0e1117 70%);
}
.block-container { padding-top: 8vh !important; }
</style>
"""

# Gentle fade for the whole app view, so the dashboard eases in (not choppy).
FADE_CSS = """
<style>
[data-testid="stAppViewContainer"] {
  animation: datamon-fade 1.1s ease-out both;
}
@keyframes datamon-fade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stAppViewContainer"] { animation: none; }
}
</style>
"""


def render_loading(st_module) -> None:
    """Full-screen GIF loader that takes over while the app boots."""
    st = st_module
    st.markdown(_LOADER_CSS, unsafe_allow_html=True)
    if LOADER_GIF.is_file():
        left, mid, right = st.columns([1, 2, 1])
        with mid:
            st.image(str(LOADER_GIF), use_container_width=True)
    else:
        st.info("Welcome to DataMon — starting the quality monitor…")


def render_fade(st_module) -> None:
    """Fade the dashboard in on the first render after the loader."""
    st_module.markdown(FADE_CSS, unsafe_allow_html=True)
