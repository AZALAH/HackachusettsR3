"""Post-login loading screen and welcome transition for DataMon.

Streamlit sanitizes `st.markdown` HTML and will not run a full-screen animated
overlay from it. So the loader is rendered with `st.components.v1.html`, which
runs in an iframe that executes real CSS/JS. The iframe owns the whole 9-second
timeline client-side: a robot crawls left-to-right in lockstep with the bar, over
a "Welcome to DataMon" splash.

The pop-in can't be done from inside the iframe (it can't touch Streamlit's own
DOM), so it is injected as a tiny JS snippet that reaches `window.parent.document`
and animates the real app container once, on the first render after the loader.
"""

from __future__ import annotations

import streamlit.components.v1 as components

LOADING_SECONDS = 9


def loading_html(seconds: int = LOADING_SECONDS) -> str:
    """Self-contained animated loader markup (used in an iframe and in tests)."""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    html,body {{ margin:0; height:100%; overflow:hidden;
      font-family: "Source Sans Pro", system-ui, sans-serif; }}
    .datamon-intro {{
      position:fixed; inset:0; display:flex; align-items:center;
      justify-content:center;
      background: radial-gradient(1200px 600px at 50% 40%, #13303a 0%, #0e1117 70%);
    }}
    .datamon-card {{ width:min(620px,88vw); text-align:center; }}
    .datamon-welcome {{ font-size:2.3rem; font-weight:800; color:#e6edf3;
      opacity:0; animation:rise .8s ease forwards; }}
    .datamon-welcome span {{ color:#2dd4bf; }}
    .datamon-sub {{ color:#9fb3c8; margin:.4rem 0 1.6rem; opacity:0;
      animation:rise .8s ease .25s forwards; }}
    .datamon-track {{ position:relative; height:30px; border-radius:16px;
      background:rgba(255,255,255,.06); border:1px solid rgba(45,212,191,.4); }}
    .datamon-fill {{ height:100%; width:0%; border-radius:16px;
      background:linear-gradient(90deg,#2dd4bf,#0d9488);
      animation:grow {seconds}s linear forwards; }}
    .datamon-robot {{ position:absolute; top:-20px; left:0; font-size:2.1rem;
      animation:drive {seconds}s linear forwards, bob .5s ease-in-out infinite; }}
    .datamon-pct {{ margin-top:1rem; color:#2dd4bf; font-weight:700;
      animation:pulse 1.2s ease-in-out infinite; }}
    @keyframes grow {{ from{{width:0%}} to{{width:100%}} }}
    @keyframes drive {{ from{{left:0}} to{{left:calc(100% - 2.1rem)}} }}
    @keyframes bob {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-5px)}} }}
    @keyframes rise {{ from{{opacity:0;transform:translateY(10px)}}
      to{{opacity:1;transform:translateY(0)}} }}
    @keyframes pulse {{ 0%,100%{{opacity:.55}} 50%{{opacity:1}} }}
    @media (prefers-reduced-motion: reduce) {{
      .datamon-fill{{width:100%;animation:none}}
      .datamon-robot{{left:calc(100% - 2.1rem);animation:none}}
      .datamon-welcome,.datamon-sub,.datamon-pct{{opacity:1;animation:none}}
    }}
    </style></head><body>
      <div class="datamon-intro"><div class="datamon-card">
        <div class="datamon-welcome">Welcome to <span>DataMon</span></div>
        <div class="datamon-sub">Starting the quality monitor…</div>
        <div class="datamon-track"><div class="datamon-fill"></div>
          <div class="datamon-robot">&#129302;</div></div>
        <div class="datamon-pct">Loading…</div>
      </div></div>
    </body></html>"""


# JS runs inside a component iframe but reaches up to the parent (the real
# Streamlit app document) to animate the app container into place once.
_POPIN_JS = """<script>
(function () {
  try {
    var doc = window.parent.document;
    var app = doc.querySelector('[data-testid="stAppViewContainer"]')
              || doc.querySelector('section.main') || doc.body;
    if (!app) return;
    var reduce = window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return;
    var style = doc.createElement('style');
    style.textContent =
      '@keyframes datamonPopin{0%{opacity:0;transform:translateY(16px) scale(.985)}'
      + '100%{opacity:1;transform:translateY(0) scale(1)}}';
    doc.head.appendChild(style);
    app.style.animation = 'datamonPopin .7s cubic-bezier(.2,.8,.2,1) both';
  } catch (e) { /* cross-origin or missing node: skip quietly */ }
})();
</script>"""


def render_loading(st_module, seconds: int = LOADING_SECONDS) -> None:
    """Render the animated loader as an iframe component (fills the viewport)."""
    components.html(loading_html(seconds), height=520, scrolling=False)


def render_popin(st_module) -> None:
    """Trigger the one-time app-container pop-in via a parent-reaching script."""
    components.html(_POPIN_JS, height=0)
