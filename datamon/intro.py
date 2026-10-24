"""Post-login loading screen and the "pop into place" dashboard reveal.

Both are real browser animations, rendered with ``st.html(...,
unsafe_allow_javascript=True)``. That runs a small script in the page itself
(not in an iframe) and avoids the two problems the earlier attempts hit:

* Streamlit re-runs restart CSS-only animations. Here the loader's progress is
  driven by a script that measures elapsed time, and the script runs once
  because no re-run happens while the loader is up (Python is busy warming
  caches, then waiting).
* CSS can't wait for Streamlit to finish drawing the dashboard. The reveal
  script hides the page, waits until the new run has replaced everything, then
  animates each tile in with a short stagger, like a console home screen.

Only trusted, static markup from this module is rendered this way. No user
input is ever placed in these templates. Animations use only ``transform`` and
``opacity`` and are skipped under ``prefers-reduced-motion``.
"""

from __future__ import annotations

import json
import time
from typing import Callable, Optional

from datamon.art import CAR_SVG, mascot_img, svg_data_uri
from datamon.funfacts import pick_cards

LOADING_SECONDS = 9
FADE_OUT_SECONDS = 0.7
CARDS_PER_LOAD = 3

# Phase messages follow what the warm-up really does, in order.
LOADER_PHASES = [
    (0, "Starting the quality monitor\u2026"),
    (22, "Loading DROID-100 recordings\u2026"),
    (48, "Scoring every episode\u2026"),
    (74, "Calibrating the anomaly baseline\u2026"),
    (96, "Ready!"),
]


def _js_json(value) -> str:
    """JSON for embedding inside a <script> tag (no early </script> close)."""
    return json.dumps(value).replace("</", "<\\/")


# Shown during the loader run only: hide Streamlit chrome under the overlay.
_LOADER_CHROME_CSS = """
<style>
[data-testid="stHeader"], [data-testid="stSidebar"] { display: none !important; }
[data-testid="stAppViewContainer"], .stApp { background: #0e1117 !important; }
</style>
"""

_LOADER_TEMPLATE = """
<style>
.dm-loader{position:fixed;inset:0;z-index:999990;background:#0e1117;
  display:flex;align-items:center;justify-content:center;color:#e6edf3;
  font-family:"Source Sans Pro",system-ui,sans-serif;
  transition:opacity .7s ease-in}
.dm-loader.dm-out{opacity:0;pointer-events:none}
.dm-l-inner{width:min(640px,88vw);text-align:center}
.dm-l-mascot{display:inline-block;animation:dm-l-float 2.8s ease-in-out infinite}
.dm-l-title{font-size:clamp(1.9rem,4.4vw,2.9rem);font-weight:800;margin:.5rem 0 .1rem;
  letter-spacing:-.01em}
.dm-l-title b{color:#2dd4bf}
.dm-l-sub{color:#9fb3c8;font-weight:600;min-height:1.5em;margin:0 0 2.4rem}
.dm-l-track{position:relative;height:30px}
.dm-l-car{position:absolute;left:0;bottom:-2px;width:48px;height:44px;
  will-change:transform}
.dm-l-car img{display:block;width:48px;height:44px;
  animation:dm-l-bump .32s ease-in-out infinite alternate}
.dm-l-bar{height:28px;border-radius:14px;background:#13303a;
  border:1px solid #2dd4bf;overflow:hidden;position:relative}
.dm-l-fill{position:absolute;inset:0;transform-origin:left center;
  transform:scaleX(0);will-change:transform;
  background:linear-gradient(90deg,#0d9488,#2dd4bf)}
.dm-l-fill::after{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(115deg,rgba(255,255,255,.13) 0 12px,
  transparent 12px 24px);animation:dm-l-stripes 1s linear infinite}
.dm-l-pct{color:#2dd4bf;font-weight:800;font-size:1.25rem;margin-top:.7rem;
  font-variant-numeric:tabular-nums}
.dm-l-card{margin:2rem auto 0;max-width:560px;min-height:5.2rem;padding:.9rem 1.1rem;
  border-radius:14px;background:rgba(45,212,191,.07);
  border:1px solid rgba(45,212,191,.25);text-align:left;
  transition:opacity .35s ease,transform .35s ease}
.dm-l-card.dm-swap{opacity:0;transform:translateY(8px)}
.dm-l-label{display:inline-block;font-size:.72rem;font-weight:800;
  letter-spacing:.12em;color:#0e1117;background:#2dd4bf;border-radius:6px;
  padding:.1rem .45rem;margin-bottom:.35rem}
.dm-l-text{margin:0;line-height:1.45;color:#dbe7ec}
.dm-l-dots{margin-top:.7rem;display:flex;gap:.4rem;justify-content:center}
.dm-l-dots span{width:7px;height:7px;border-radius:50%;background:#27424d;
  transition:background .3s}
.dm-l-dots span.on{background:#2dd4bf}
@keyframes dm-l-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes dm-l-bump{from{transform:translateY(0)}to{transform:translateY(-2px)}}
@keyframes dm-l-stripes{from{transform:translateX(0)}to{transform:translateX(-26px)}}
@media (prefers-reduced-motion: reduce){
  .dm-l-mascot,.dm-l-car img,.dm-l-fill::after{animation:none}
  .dm-l-card{transition:none}}
</style>
<div class="dm-loader" role="progressbar" aria-label="Loading DataMon"
     aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
  <div class="dm-l-inner">
    <div class="dm-l-mascot">__MASCOT__</div>
    <div class="dm-l-title">Welcome to Data<b>Mon</b></div>
    <p class="dm-l-sub" aria-live="polite">Starting the quality monitor&hellip;</p>
    <div class="dm-l-track"><div class="dm-l-car">
      <img src="__CAR__" alt="" width="48" height="44"></div></div>
    <div class="dm-l-bar"><div class="dm-l-fill"></div></div>
    <div class="dm-l-pct">0%</div>
    <div class="dm-l-card" aria-live="polite">
      <span class="dm-l-label"></span><p class="dm-l-text"></p></div>
    <div class="dm-l-dots" aria-hidden="true">__DOTS__</div>
  </div>
</div>
<script>
(function () {
  var root = document.currentScript.parentNode.querySelector(".dm-loader");
  if (!root) { return; }
  var DURATION = __DURATION_MS__, FADE = __FADE_MS__;
  var CARDS = __CARDS__, PHASES = __PHASES__;
  var fill = root.querySelector(".dm-l-fill"), car = root.querySelector(".dm-l-car");
  var bar = root.querySelector(".dm-l-bar"), pct = root.querySelector(".dm-l-pct");
  var sub = root.querySelector(".dm-l-sub"), card = root.querySelector(".dm-l-card");
  var label = root.querySelector(".dm-l-label"), text = root.querySelector(".dm-l-text");
  var dots = root.querySelectorAll(".dm-l-dots span");
  var start = performance.now(), shownCard = -1, shownPhase = -1, lastPct = -1;
  function showCard(i) {
    shownCard = i;
    for (var d = 0; d < dots.length; d++) { dots[d].className = d === i ? "on" : ""; }
    card.classList.add("dm-swap");
    setTimeout(function () {
      label.textContent = CARDS[i].label; text.textContent = CARDS[i].text;
      card.classList.remove("dm-swap");
    }, i === 0 ? 0 : 320);
  }
  function frame(now) {
    if (!document.contains(root)) { return; }
    var t = Math.min(1, (now - start) / (DURATION - FADE));
    var eased = 1 - Math.pow(1 - t, 2.2);
    var p = Math.round(eased * 100);
    fill.style.transform = "scaleX(" + eased + ")";
    car.style.transform = "translateX(" + ((bar.clientWidth - 48) * eased) + "px)";
    if (p !== lastPct) {
      lastPct = p; pct.textContent = p + "%"; root.setAttribute("aria-valuenow", p);
    }
    var phase = 0;
    for (var k = 0; k < PHASES.length; k++) { if (p >= PHASES[k][0]) { phase = k; } }
    if (phase !== shownPhase) { shownPhase = phase; sub.textContent = PHASES[phase][1]; }
    var c = Math.min(CARDS.length - 1,
                     Math.floor((now - start) / (DURATION / CARDS.length)));
    if (c !== shownCard) { showCard(c); }
    if (now - start >= DURATION - FADE) { root.classList.add("dm-out"); return; }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
</script>
"""


def loader_html(
    total_seconds: float = LOADING_SECONDS, cards: Optional[list] = None,
) -> str:
    """The loader overlay markup + script (pure; unit-testable)."""
    chosen = cards if cards is not None else pick_cards(CARDS_PER_LOAD)
    payload = [{"label": card.label, "text": card.text} for card in chosen]
    return (
        _LOADER_TEMPLATE
        .replace("__MASCOT__", mascot_img(84))
        .replace("__CAR__", svg_data_uri(CAR_SVG))
        .replace("__DOTS__", "<span></span>" * len(payload))
        .replace("__DURATION_MS__", str(int(total_seconds * 1000)))
        .replace("__FADE_MS__", str(int(FADE_OUT_SECONDS * 1000)))
        .replace("__CARDS__", _js_json(payload))
        .replace("__PHASES__", _js_json(LOADER_PHASES))
    )


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
    st.markdown(_LOADER_CHROME_CSS, unsafe_allow_html=True)
    st.html(loader_html(total_seconds), unsafe_allow_javascript=True)

    if warmup is not None:
        try:
            warmup()
        except Exception:  # the dashboard will surface any real error itself
            pass

    remaining = total_seconds - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)


_REVEAL_TEMPLATE = """
<style>
html.dm-revealing [data-testid="stMainBlockContainer"],
html.dm-revealing [data-testid="stSidebarUserContent"] { opacity: 0 !important; }
</style>
<div class="dm-hide-slot"></div>
<script>
(function () {
  var doc = document.documentElement, token = "__TOKEN__";
  if (doc.getAttribute("data-dm-revealed") === token) { return; }
  doc.setAttribute("data-dm-revealed", token);
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { return; }
  doc.classList.add("dm-revealing");
  var start = performance.now(), calm = 0;
  function settled() {
    return !document.querySelector('[data-stale="true"]') &&
           document.querySelector('[data-testid="stTabs"], .stTabs');
  }
  function kids(selector) {
    var block = document.querySelector(selector);
    if (!block) { return []; }
    return Array.prototype.filter.call(block.children, function (el) {
      return el.offsetHeight > 0 && !el.querySelector("#datamon-help-anchor");
    });
  }
  function pop() {
    var side = kids('[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]');
    var main = kids('[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]');
    var tiles = document.querySelectorAll('[data-testid="stMetric"]');
    doc.classList.remove("dm-revealing");
    var ease = "cubic-bezier(.2,.9,.25,1.2)";
    side.forEach(function (el, i) {
      el.animate([{opacity: 0, transform: "translateX(-28px)"},
                  {opacity: 1, transform: "none"}],
                 {duration: 480, delay: 60 + i * 55, easing: ease, fill: "backwards"});
    });
    main.forEach(function (el, i) {
      el.animate([{opacity: 0, transform: "translateY(26px) scale(.95)"},
                  {opacity: 1, transform: "none"}],
                 {duration: 560, delay: 120 + i * 75, easing: ease, fill: "backwards"});
    });
    Array.prototype.forEach.call(tiles, function (el, i) {
      el.animate([{opacity: 0, transform: "scale(.7)"},
                  {opacity: 1, transform: "scale(1.04)", offset: .7},
                  {opacity: 1, transform: "none"}],
                 {duration: 520, delay: 420 + main.length * 75 + i * 90,
                  easing: "ease-out", fill: "backwards"});
    });
  }
  function wait() {
    calm = settled() ? calm + 1 : 0;
    if (calm >= 6 || performance.now() - start > 3500) { pop(); return; }
    requestAnimationFrame(wait);
  }
  requestAnimationFrame(wait);
})();
</script>
"""


def reveal_html(token: str) -> str:
    """Markup + script that pops the dashboard tiles into place (pure)."""
    safe = "".join(ch for ch in str(token) if ch.isalnum())[:32]
    return _REVEAL_TEMPLATE.replace("__TOKEN__", safe)


def render_reveal(st_module, token: str) -> None:
    """Pop the dashboard into place, once per sign-in ``token``."""
    st_module.html(reveal_html(token), unsafe_allow_javascript=True)
