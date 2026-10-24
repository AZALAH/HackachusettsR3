"""Post-login loading screen and welcome transition for DataMon.

Shown once, right after a successful sign-in: a themed progress bar with a little
robot car driving along it, a "Welcome to DataMon" title, then the app pops into
place. Honors reduced-motion by collapsing to a short, static splash instead of
the full animation.
"""

from __future__ import annotations

LOADING_SECONDS = 9


def loading_html(seconds: int = LOADING_SECONDS) -> str:
    """Full-bleed robot-driving loader that fills over ``seconds``."""
    return f"""
    <div class="datamon-intro">
      <div class="datamon-intro-card">
        <div class="datamon-welcome">Welcome to <span>DataMon</span></div>
        <div class="datamon-sub">Starting the quality monitor…</div>
        <div class="datamon-track">
          <div class="datamon-fill"></div>
          <div class="datamon-robot" aria-hidden="true">🤖</div>
        </div>
        <div class="datamon-pct">Loading…</div>
      </div>
    </div>
    <style>
    .datamon-intro {{
      position: fixed; inset: 0; z-index: 9999;
      display: flex; align-items: center; justify-content: center;
      background: radial-gradient(1200px 600px at 50% 40%,
                  #13303a 0%, #0e1117 70%);
    }}
    .datamon-intro-card {{ width: min(560px, 86vw); text-align: center; }}
    .datamon-welcome {{
      font-size: 2.2rem; font-weight: 800; color: #e6edf3;
      opacity: 0; animation: datamon-rise 0.8s ease forwards;
    }}
    .datamon-welcome span {{ color: #2dd4bf; }}
    .datamon-sub {{
      color: #9fb3c8; margin: 0.4rem 0 1.4rem;
      opacity: 0; animation: datamon-rise 0.8s ease 0.25s forwards;
    }}
    .datamon-track {{
      position: relative; height: 26px; border-radius: 14px;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(45,212,191,0.35); overflow: hidden;
    }}
    .datamon-fill {{
      height: 100%; width: 0%; border-radius: 14px;
      background: linear-gradient(90deg, #2dd4bf, #0d9488);
      animation: datamon-grow {seconds}s linear forwards;
    }}
    .datamon-robot {{
      position: absolute; top: -14px; left: 0; font-size: 2rem;
      animation: datamon-drive {seconds}s linear forwards,
                 datamon-bob 0.6s ease-in-out infinite;
    }}
    .datamon-pct {{ margin-top: 0.8rem; color: #2dd4bf; font-weight: 700; }}
    @keyframes datamon-grow {{ from {{ width: 0%; }} to {{ width: 100%; }} }}
    @keyframes datamon-drive {{
      from {{ left: 0; }} to {{ left: calc(100% - 2rem); }}
    }}
    @keyframes datamon-bob {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(-4px); }}
    }}
    @keyframes datamon-rise {{
      from {{ opacity: 0; transform: translateY(10px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    /* The app content underneath pops into place after the loader clears. */
    @keyframes datamon-popin {{
      from {{ opacity: 0; transform: scale(0.98); }}
      to {{ opacity: 1; transform: scale(1); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .datamon-fill, .datamon-robot {{ animation-duration: 0.01s; }}
      .datamon-welcome, .datamon-sub {{ animation: none; opacity: 1; }}
    }}
    </style>
    """


POPIN_CSS = """
<style>
section.main > div.block-container {
  animation: datamon-popin 0.6s ease both;
}
@keyframes datamon-popin {
  from { opacity: 0; transform: translateY(12px) scale(0.99); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@media (prefers-reduced-motion: reduce) {
  section.main > div.block-container { animation: none; }
}
</style>
"""
