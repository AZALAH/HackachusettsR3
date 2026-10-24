"""Shared visual branding for the DataMon portal and login page.

One place for the look-and-feel, so the dashboard and the (upcoming) login page
stay visually consistent: a teal wordmark, tightened headings, softer cards, and
a subtle gradient header band. All colors key off the Streamlit theme variables
from ``.streamlit/config.toml`` so light/dark both stay readable.
"""

from __future__ import annotations

from datamon.art import mascot_img

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

/* Sidebar: start content right under the collapse arrow (clock sits here). */
[data-testid="stSidebarUserContent"] {{ padding-top: 0 !important; }}
[data-testid="stSidebarHeader"] {{ margin-bottom: 0 !important; }}

/* Hide the chain-link anchor icons Streamlit adds next to headings. */
[data-testid="stHeaderActionElements"] {{ display: none !important; }}

/* Leave room above the content for the header clock and the sidebar arrow. */
[data-testid="stMainBlockContainer"] {{ padding-top: 4rem !important; }}

/* Script-only helpers (reveal animation) take no space in the layout. */
[data-testid="stElementContainer"]:has(.dm-hide-slot) {{ display: none !important; }}

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

_WORDMARK = """
<div class="dm-wordmark">
  <div class="dm-wm-name">Data<span>Mon</span></div>
  <div class="dm-wm-sub">Robot data-collection quality monitor</div>
</div>
"""

_HEADER_CSS = """
<style>
.dm-brand{display:flex;align-items:center;gap:1.1rem;padding:.2rem 0 .4rem;
  color:#e6edf3;font-family:"Source Sans Pro",system-ui,sans-serif}
.dm-brand-logo{display:flex;align-items:center;gap:.8rem}
.dm-wm-name{font-size:1.9rem;font-weight:800;line-height:1;letter-spacing:-.01em}
.dm-wm-name span{color:#2dd4bf}
.dm-wm-sub{font-size:.85rem;opacity:.72;margin-top:.2rem}
</style>
"""

# A robot-head clock face. Hour marks are the numbers 1-12 written in binary,
# like a classic binary wall clock. Static markup is built here; a tiny script
# moves the hands every second using the VIEWER's local time.
_CLOCK_SIZE = 176
_CLOCK_CSS = """
<style>
.dm-clock{position:relative;display:flex;flex-direction:column;align-items:center;
  gap:.3rem;flex:none}
.dm-clock-head{position:relative;width:__SIZE__px;height:__SIZE__px;
  margin-top:14px}
.dm-clock-antenna{position:absolute;left:50%;top:-14px;width:3px;height:14px;
  margin-left:-1.5px;background:#9fb3c0;border-radius:2px}
.dm-clock-antenna::before{content:"";position:absolute;left:50%;top:-6px;
  width:9px;height:9px;margin-left:-4.5px;border-radius:50%;background:#2dd4bf;
  box-shadow:0 0 8px #2dd4bf;animation:dm-clock-led 2s ease-in-out infinite}
.dm-clock-ear{position:absolute;top:50%;width:9px;height:26px;margin-top:-13px;
  border-radius:4px;background:#9fb3c0}
.dm-clock-ear.l{left:-6px}.dm-clock-ear.r{right:-6px}
.dm-clock-face{position:absolute;inset:0;border-radius:50%;
  background:radial-gradient(circle at 50% 38%,#1c2a33,#0f171d 70%);
  border:3px solid #2dd4bf;box-shadow:0 0 0 3px #1f2937,0 6px 18px rgba(0,0,0,.35),
  inset 0 0 14px rgba(45,212,191,.18)}
.dm-clock-num{position:absolute;transform:translate(-50%,-50%);
  font:700 __NUM__px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color:#c9e9e3;letter-spacing:.02em}
.dm-clock-hand{position:absolute;left:50%;bottom:50%;transform-origin:50% 100%;
  border-radius:3px;transform:translateX(-50%) rotate(0deg)}
.dm-clock-hand.h{width:5px;height:21%;background:#dbe7ec}
.dm-clock-hand.m{width:3.5px;height:28%;background:#dbe7ec}
.dm-clock-hand.s{width:1.6px;height:31%;background:#2dd4bf}
.dm-clock-eye{position:absolute;left:50%;top:50%;width:13px;height:13px;
  margin:-6.5px 0 0 -6.5px;border-radius:50%;background:#2dd4bf;
  border:3px solid #1f2937}
.dm-clock-read{text-align:center;line-height:1.15}
.dm-clock-bin{font:700 .95rem ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color:#2dd4bf;letter-spacing:.04em}
.dm-clock-dec{font-size:.85rem;opacity:.75}
@keyframes dm-clock-led{0%,100%{opacity:1}50%{opacity:.35}}
@media (prefers-reduced-motion: reduce){.dm-clock-antenna::before{animation:none}}
</style>
"""

_CLOCK_SCRIPT = """
<script>
(function () {
  var host = document.currentScript.parentNode;
  var clock = host.querySelector(".dm-clock");
  if (!clock) { return; }
  var h = clock.querySelector(".dm-clock-hand.h"), m = clock.querySelector(".dm-clock-hand.m");
  var s = clock.querySelector(".dm-clock-hand.s");
  var bin = clock.querySelector(".dm-clock-bin"), dec = clock.querySelector(".dm-clock-dec");
  function turn(el, deg) { el.style.transform = "translateX(-50%) rotate(" + deg + "deg)"; }
  function pad(n, w, c) { n = String(n); while (n.length < w) { n = c + n; } return n; }
  var timer = null;
  function tick() {
    if (!document.contains(clock)) { clearInterval(timer); return; }
    var d = new Date(), hh = d.getHours(), mm = d.getMinutes(), ss = d.getSeconds();
    turn(h, (hh % 12) * 30 + mm * 0.5);
    turn(m, mm * 6 + ss * 0.1);
    turn(s, ss * 6);
    var h12 = hh % 12 || 12, ampm = hh < 12 ? "AM" : "PM";
    bin.textContent = h12.toString(2) + " : " + pad(mm.toString(2), 6, "0");
    var said = h12 + ":" + pad(mm, 2, "0") + " " + ampm;
    dec.textContent = said;
    clock.setAttribute("aria-label", "Current time, " + said);
  }
  tick();
  timer = setInterval(tick, 1000);
})();
</script>
"""


def clock_html(size: int = _CLOCK_SIZE) -> str:
    """Static markup for the robot binary clock (hands are moved by script)."""
    import math

    center = size / 2
    numerals = []
    for hour in range(1, 13):
        angle = math.radians(hour * 30)
        radius = size * 0.355
        x = center + radius * math.sin(angle)
        y = center - radius * math.cos(angle)
        numerals.append(
            f'<span class="dm-clock-num" style="left:{x:.1f}px;top:{y:.1f}px">'
            f"{hour:b}</span>"
        )
    return (
        _CLOCK_CSS.replace("__SIZE__", str(size))
        .replace("__NUM__", f"{size * 0.066:.1f}")
        + '<div class="dm-clock" role="img" aria-label="Current time">'
        + '<div class="dm-clock-head">'
        + '<div class="dm-clock-antenna"></div>'
        + '<div class="dm-clock-ear l"></div><div class="dm-clock-ear r"></div>'
        + '<div class="dm-clock-face">'
        + "".join(numerals)
        + '<div class="dm-clock-hand h"></div><div class="dm-clock-hand m"></div>'
        + '<div class="dm-clock-hand s"></div><div class="dm-clock-eye"></div>'
        + "</div></div>"
        + '<div class="dm-clock-read"><div class="dm-clock-bin">-- : ------</div>'
        + '<div class="dm-clock-dec">&nbsp;</div></div>'
        + "</div>"
    )


def brand_header_html(*, logo_size: int = 64, clock: bool = False) -> str:
    """The DataMon header: optional binary clock, animated mascot, wordmark."""
    parts = [_HEADER_CSS, '<div class="dm-brand">']
    if clock:
        parts.append(clock_html())
    parts.append('<div class="dm-brand-logo">')
    parts.append(mascot_img(logo_size))
    parts.append(_WORDMARK)
    parts.append("</div></div>")
    if clock:
        parts.append(_CLOCK_SCRIPT)
    return "".join(parts)


def inject_global_css(st_module) -> None:
    """Apply the shared CSS polish. Safe to call once near the top of a page."""
    st_module.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def render_clock(st_module, size: int = _CLOCK_SIZE) -> None:
    """Render the live robot binary clock, centred, in the given container."""
    st_module.html(
        '<div style="display:flex;justify-content:center;padding:.1rem 0 .6rem">'
        + clock_html(size) + "</div>" + _CLOCK_SCRIPT,
        unsafe_allow_javascript=True,
    )


def render_brand_header(st_module, *, clock: bool = False) -> None:
    """Render the DataMon header (with the live clock on the dashboard)."""
    st_module.html(
        brand_header_html(clock=clock), unsafe_allow_javascript=clock,
    )


# --- Login page --------------------------------------------------------------

_LOGIN_CSS = """
<style>
/* Blueprint grid + teal glow, drawn once as a static background. */
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(900px 520px at 50% 18%, rgba(45,212,191,.16), transparent 70%),
    linear-gradient(rgba(45,212,191,.055) 1px, transparent 1px) 0 0 / 40px 40px,
    linear-gradient(90deg, rgba(45,212,191,.055) 1px, transparent 1px) 0 0 / 40px 40px,
    #0b1016 !important;
}
[data-testid="stHeader"] { display: none !important; }
[data-testid="stMainBlockContainer"] { padding-top: 7vh !important; }
.dm-login-hero{text-align:center;color:#e6edf3;
  font-family:"Source Sans Pro",system-ui,sans-serif}
.dm-login-hero .dm-float{display:inline-block;
  animation:dm-login-float 3s ease-in-out infinite}
.dm-login-name{font-size:2.6rem;font-weight:800;line-height:1;margin-top:.7rem;
  letter-spacing:-.015em}
.dm-login-name span{color:#2dd4bf}
.dm-login-tag{opacity:.8;margin-top:.35rem}
.dm-login-chips{display:flex;gap:.35rem;justify-content:center;flex-wrap:wrap;
  margin:.9rem 0 .3rem}
.dm-login-chips span{font-size:.74rem;font-weight:700;letter-spacing:.04em;
  padding:.18rem .6rem;border-radius:999px;color:#99f6e4;
  border:1px solid rgba(45,212,191,.35);background:rgba(45,212,191,.08)}
/* The sign-in form becomes a glowing glass card. */
[data-testid="stForm"] {
  background: rgba(17,26,33,.82) !important;
  border: 1px solid rgba(45,212,191,.45) !important;
  border-radius: 16px !important; padding: 1.4rem 1.4rem 1.1rem !important;
  box-shadow: 0 0 0 1px rgba(45,212,191,.08), 0 18px 50px rgba(0,0,0,.45),
              0 0 40px rgba(45,212,191,.12);
}
[data-testid="stForm"] button { width: 100%; }
/* A little robot car patrols a track along the bottom of the screen. */
.dm-login-track{position:fixed;left:0;right:0;bottom:0;height:54px;
  pointer-events:none;z-index:0;
  background:repeating-linear-gradient(90deg,rgba(45,212,191,.35) 0 18px,
    transparent 18px 34px) 0 40px / 100% 3px no-repeat}
.dm-login-car{position:absolute;bottom:14px;left:0;width:48px;height:44px;
  animation:dm-login-drive 16s linear infinite;will-change:transform}
@keyframes dm-login-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes dm-login-drive{from{transform:translateX(-60px)}
  to{transform:translateX(calc(100vw + 60px))}}
@media (prefers-reduced-motion: reduce){
  .dm-login-hero .dm-float,.dm-login-car{animation:none}}
</style>
"""


def login_hero_html() -> str:
    """Branded hero for the sign-in page (static markup + CSS animations)."""
    from datamon.art import CAR_SVG, svg_data_uri

    return (
        _LOGIN_CSS
        + '<div class="dm-login-hero">'
        + f'<div class="dm-float">{mascot_img(104)}</div>'
        + '<div class="dm-login-name">Data<span>Mon</span></div>'
        + '<div class="dm-login-tag">Quality control for robot training data: '
        + "bad demonstrations stop here.</div>"
        + '<div class="dm-login-chips"><span>ROBOTICS &amp; HARDWARE</span>'
        + "<span>DROID</span><span>BRIDGEDATA</span><span>LEROBOT</span></div>"
        + "</div>"
        + '<div class="dm-login-track">'
        + f'<img class="dm-login-car" src="{svg_data_uri(CAR_SVG)}" alt="">'
        + "</div>"
    )


def render_login_hero(st_module) -> None:
    st_module.html(login_hero_html())
