"""Shared visual branding for the DataMon portal and login page.

One place for the look-and-feel, so the dashboard and the (upcoming) login page
stay visually consistent: a teal wordmark, tightened headings, softer cards, and
a subtle gradient header band. All colors key off the Streamlit theme variables
from ``.streamlit/config.toml`` so light/dark both stay readable.
"""

from __future__ import annotations

PRIMARY = "#2dd4bf"
PRIMARY_DEEP = "#0d9488"

_GLOBAL_CSS = f"""
<style>
:root {{
  --datamon-primary: {PRIMARY};
  --datamon-primary-deep: {PRIMARY_DEEP};
}}

/* Tighter, more intentional headings */
h1, h2, h3 {{ letter-spacing: -0.01em; }}

/* Primary buttons: gradient fill, subtle lift on hover */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {{
  background: linear-gradient(135deg, var(--datamon-primary),
              var(--datamon-primary-deep));
  border: none; color: #052e2b; font-weight: 700;
}}
.stButton > button:hover {{ transform: translateY(-1px); transition: .15s ease; }}

/* Metrics read as cards */
div[data-testid="stMetric"] {{
  background: rgba(45, 212, 191, 0.06);
  border: 1px solid rgba(45, 212, 191, 0.18);
  border-radius: 12px; padding: 0.6rem 0.9rem;
}}

/* Bordered containers get a soft shadow */
div[data-testid="stVerticalBlockBorderWrapper"] {{
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  border-radius: 12px;
}}

/* Active tab underline in the brand color */
.stTabs [aria-selected="true"] {{ color: var(--datamon-primary) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{
  background-color: var(--datamon-primary) !important;
}}

@media (prefers-reduced-motion: reduce) {{
  .stButton > button:hover {{ transform: none; }}
  [data-testid="stExpandSidebarButton"] {{ animation: none !important; }}
}}

/* Hide only the right-hand toolbar actions (deploy, main menu, running
   indicator). The toolbar itself must stay: Streamlit puts the "reopen sidebar"
   arrow inside it, and hiding the whole toolbar strands a collapsed sidebar. */
[data-testid="stToolbarActions"],
[data-testid="stMainMenu"],
[data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"],
div[data-testid="manage-app-button"],
.stAppDeployButton,
.stDeployButton {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent !important; }}

/* Make the "reopen sidebar" arrow obvious: teal, outlined, gently glowing. */
[data-testid="stExpandSidebarButton"] {{
  display: inline-flex !important; visibility: visible !important;
  background: rgba(45, 212, 191, 0.14) !important;
  border: 1px solid var(--datamon-primary) !important;
  border-radius: 10px !important;
  box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.5);
  animation: datamon-glow 2.4s ease-in-out infinite;
}}
[data-testid="stExpandSidebarButton"] * {{
  color: var(--datamon-primary) !important;
  fill: var(--datamon-primary) !important;
}}
@keyframes datamon-glow {{
  0%, 100% {{ box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.45); }}
  50% {{ box-shadow: 0 0 0 6px rgba(45, 212, 191, 0); }}
}}

/* Smoothness: Streamlit dims every element from the previous run while the
   script re-runs, which reads as flicker on each click. Keep them steady. */
[data-stale="true"] {{ opacity: 1 !important; transition: none !important; }}

/* Narration and alert sounds play without showing a media player. */
[data-testid="stElementContainer"]:has([data-testid="stAudio"]),
[data-testid="stAudio"] {{ display: none !important; }}

/* Hide per-element hover toolbars (edit pencil, fullscreen, etc.). */
[data-testid="stElementToolbar"],
[data-testid="StyledFullScreenButton"],
button[title="View fullscreen"] {{ display: none !important; }}

/* Help panel: solid readable surface, not translucent over content. */
div[data-testid="stExpander"]:has(#datamon-help-anchor) summary {{
  background: var(--secondary-background-color, #1a1f2b);
  font-weight: 700;
}}
div[data-testid="stExpander"]:has(#datamon-help-anchor) {{
  background: var(--secondary-background-color, #1a1f2b);
}}
</style>
"""

_HEADER = """
<div style="display:flex;align-items:center;gap:0.65rem;
            padding:0.4rem 0 0.2rem;">
  <div style="width:38px;height:38px;border-radius:10px;
              background:linear-gradient(135deg,#2dd4bf,#0d9488);
              display:flex;align-items:center;justify-content:center;
              font-size:1.3rem;">🛡️</div>
  <div>
    <div style="font-size:1.5rem;font-weight:800;line-height:1;">
      Data<span style="color:#2dd4bf;">Mon</span></div>
    <div style="font-size:0.8rem;opacity:0.7;">
      Robot data-collection quality monitor</div>
  </div>
</div>
"""


def inject_global_css(st_module) -> None:
    """Apply the shared CSS polish. Safe to call once near the top of a page."""
    st_module.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def render_brand_header(st_module) -> None:
    """Render the DataMon wordmark header."""
    st_module.markdown(_HEADER, unsafe_allow_html=True)
