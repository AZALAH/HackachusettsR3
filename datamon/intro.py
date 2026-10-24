"""Post-login loading screen (animated GIF) and a smooth hand-off to the app.

Streamlit re-runs on every interaction, which restarts CSS keyframe animations.
A GIF plays itself, so the loader animates reliably. The loader GIF is
pre-rendered and committed (see ``scripts/make_loader_gif.py``); the app only
displays it.

The hand-off is a cross-fade through the page background:

1. While the loader is up it owns the screen (header and sidebar hidden).
2. The loader is not idle time: ``render_loading`` runs a warm-up callback that
   loads and calibrates the default dataset, so the dashboard's first render
   is fast instead of building piece by piece.
3. In the last ``FADE_OUT_SECONDS`` the loader fades to the background colour.
4. The next run starts the dashboard at opacity 0 and eases it in, so the
   widgets Streamlit draws top-to-bottom appear together, not one by one.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

LOADING_SECONDS = 9
FADE_OUT_SECONDS = 0.7
LOADER_GIF = Path("assets/loader.gif")


def _loader_css(total_seconds: float) -> str:
    """CSS for the loader run: hide chrome, flat background, timed fade-out.

    There is no re-run while the loader is up (the script is busy warming up and
    then waiting), so this one-shot animation plays exactly once.
    """
    delay = max(0.0, total_seconds - FADE_OUT_SECONDS)
    return f"""
<style>
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="StyledFullScreenButton"],
[data-testid="stElementToolbar"],
button[title="View fullscreen"],
.stImage button {{ display: none !important; }}
[data-testid="stAppViewContainer"],
.stApp {{ background: #0e1117 !important; }}
.block-container {{
  padding-top: 10vh !important;
  animation: datamon-loader-out {FADE_OUT_SECONDS}s ease-in {delay:.2f}s forwards;
}}
@keyframes datamon-loader-out {{
  from {{ opacity: 1; }}
  to   {{ opacity: 0; }}
}}
</style>
"""


# Dashboard entrance. Starts fully transparent (``both`` holds the first frame
# during the short delay) so nothing pops in before the fade begins. Opacity
# only: a transform here would break the fixed-position help panel.
FADE_CSS = """
<style>
[data-testid="stAppViewContainer"] {
  animation: datamon-fade 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.15s both;
}
@keyframes datamon-fade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
/* On this run, anything still marked stale is a leftover from the loader
   (the GIF) waiting to be replaced. Keep it from flashing back in. */
[data-stale="true"] { visibility: hidden !important; }
@media (prefers-reduced-motion: reduce) {
  [data-testid="stAppViewContainer"] { animation: none; }
}
</style>
"""


def render_loading(
    st_module,
    warmup: Optional[Callable[[], None]] = None,
    *,
    total_seconds: float = LOADING_SECONDS,
) -> None:
    """Show the full-screen loader, run ``warmup``, and hold for the full time.

    The warm-up time counts toward ``total_seconds``, so a slow first load does
    not make the loader longer than intended. A failing warm-up never blocks
    sign-in; the dashboard simply loads its data on the next run instead.
    """
    st = st_module
    started = time.monotonic()
    st.markdown(_loader_css(total_seconds), unsafe_allow_html=True)
    if LOADER_GIF.is_file():
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.image(str(LOADER_GIF), width="stretch")
    else:
        st.info("Welcome to DataMon — starting the quality monitor…")

    if warmup is not None:
        try:
            warmup()
        except Exception:  # the dashboard will surface any real error itself
            pass

    remaining = total_seconds - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)


def render_fade(st_module) -> None:
    """Fade the dashboard in on the first render after the loader."""
    st_module.markdown(FADE_CSS, unsafe_allow_html=True)
