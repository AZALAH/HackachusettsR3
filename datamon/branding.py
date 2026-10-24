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
