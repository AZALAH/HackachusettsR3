"""Post-login loading screen and welcome transition for DataMon.

Shown once, right after a successful sign-in: a themed progress bar with a little
robot car driving slowly from left to right as the bar fills over ~9 seconds, a
"Welcome to DataMon" title, a live percentage counting up, then the app pops into
place. Honors reduced-motion by collapsing to a short, static splash.
"""

from __future__ import annotations

LOADING_SECONDS = 9


def loading_html(seconds: int = LOADING_SECONDS) -> str:
    """Full-bleed robot-driving loader that fills over ``seconds``.

    The bar fill, the robot's travel, and the counting percentage all share the
    same ``{seconds}s`` timeline so they stay in lockstep — the robot crawls the
    full width exactly as the bar reaches 100%.
    """
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
      position: fixed; inset: 0; z-index: 99999;
      display: flex; align-items: center; justify-content: center;
      background: radial-gradient(1200px 600px at 50% 40%,
                  #13303a 0%, #0e1117 70%);
    }}
    .datamon-intro-card {{ width: min(620px, 88vw); text-align: center; }}
    .datamon-welcome {{
      font-size: 2.3rem; font-weight: 800; color: #e6edf3;
      opacity: 0; animation: datamon-rise 0.8s ease forwards;
    }}
    .datamon-welcome span {{ color: #2dd4bf; }}
    .datamon-sub {{
      color: #9fb3c8; margin: 0.4rem 0 1.6rem;
      opacity: 0; animation: datamon-rise 0.8s ease 0.25s forwards;
    }}
    .datamon-track {{
      position: relative; height: 30px; border-radius: 16px;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(45,212,191,0.4); overflow: visible;
    }}
    .datamon-fill {{
      height: 100%; width: 0%; border-radius: 16px;
      background: linear-gradient(90deg, #2dd4bf, #0d9488);
      animation: datamon-grow {seconds}s linear forwards;
    }}
    /* The robot sits ABOVE the bar and crawls the full width over {seconds}s. */
    .datamon-robot {{
      position: absolute; top: -20px; left: 0; font-size: 2.1rem;
      animation: datamon-drive {seconds}s linear forwards,
                 datamon-bob 0.5s ease-in-out infinite;
    }}
    .datamon-pct {{
      margin-top: 1rem; color: #2dd4bf; font-weight: 700; font-size: 1.1rem;
      animation: datamon-pulse 1.2s ease-in-out infinite;
    }}
    @keyframes datamon-pulse {{ 0%,100% {{ opacity: 0.55; }} 50% {{ opacity: 1; }} }}
    @keyframes datamon-grow {{ from {{ width: 0%; }} to {{ width: 100%; }} }}
    @keyframes datamon-drive {{
      from {{ left: 0; }} to {{ left: calc(100% - 2.1rem); }}
    }}
    @keyframes datamon-bob {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(-5px); }}
    }}
    @keyframes datamon-rise {{
      from {{ opacity: 0; transform: translateY(10px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .datamon-fill {{ width: 100%; animation: none; }}
      .datamon-robot {{ left: calc(100% - 2.1rem); animation: none; }}
      .datamon-welcome, .datamon-sub {{ animation: none; opacity: 1; }}
      .datamon-pct {{ animation: none; opacity: 1; }}
    }}
    </style>
    """


# Applied on the first app render after the loader clears, so the whole view
# animates into place. Targets the top-level Streamlit app container, which is
# present on both local and hosted deploys.
POPIN_CSS = """
<style>
[data-testid="stAppViewContainer"] {
  animation: datamon-popin 0.7s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes datamon-popin {
  0%   { opacity: 0; transform: translateY(16px) scale(0.985); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stAppViewContainer"] { animation: none; }
}
</style>
"""
