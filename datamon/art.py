"""Small animated SVG artwork for the DataMon interface.

Streamlit's HTML sanitizer removes inline ``<svg>`` markup, so each drawing is
shipped as an ``<img>`` with a base64 ``data:`` URI. An SVG loaded as an image
still runs its own CSS animations, but it can't run scripts or reach the page,
so it is safe to inline. Every animation uses only ``transform`` and
``opacity`` (cheap for the browser to draw) and stops under
``prefers-reduced-motion``.
"""

from __future__ import annotations

import base64

SHIELD_LIGHT = "#38bdf8"
SHIELD_DEEP = "#2563eb"
TEAL = "#2dd4bf"
TEAL_DEEP = "#0d9488"
METAL = "#dbe7ec"
METAL_SHADE = "#9fb3c0"
DARK = "#1f2937"

_REDUCED_MOTION = (
    "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
)

# A mini robot holding a blue shield: DataMon's mascot and logo.
MASCOT_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
<defs>
  <linearGradient id="sh" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{SHIELD_LIGHT}"/>
    <stop offset="1" stop-color="{SHIELD_DEEP}"/>
  </linearGradient>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{TEAL}"/>
    <stop offset="1" stop-color="{TEAL_DEEP}"/>
  </linearGradient>
</defs>
<style>
  .bob{{animation:bob 2.6s ease-in-out infinite}}
  .eye{{transform-box:fill-box;transform-origin:center;
        animation:blink 4.2s infinite}}
  .led{{animation:led 1.6s ease-in-out infinite}}
  .shine{{animation:shine 3.4s ease-in-out infinite}}
  @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-2.5px)}}}}
  @keyframes blink{{0%,92%,100%{{transform:scaleY(1)}}95%{{transform:scaleY(.1)}}}}
  @keyframes led{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
  @keyframes shine{{0%,60%,100%{{opacity:0}}75%{{opacity:.55}}}}
  {_REDUCED_MOTION}
</style>
<rect width="96" height="96" rx="22" fill="url(#bg)"/>
<g class="bob">
  <line x1="40" y1="17" x2="40" y2="25" stroke="{DARK}" stroke-width="3"
        stroke-linecap="round"/>
  <circle class="led" cx="40" cy="15" r="4" fill="#fde047"/>
  <rect x="22" y="25" width="36" height="25" rx="9" fill="{METAL}"/>
  <rect x="27" y="30" width="26" height="14" rx="6" fill="{DARK}"/>
  <circle class="eye" cx="34.5" cy="37" r="3.2" fill="{TEAL}"/>
  <circle class="eye" cx="45.5" cy="37" r="3.2" fill="{TEAL}"/>
  <rect x="26" y="52" width="28" height="22" rx="7" fill="{METAL_SHADE}"/>
  <circle cx="34" cy="62" r="2.5" fill="{DARK}"/>
  <rect x="17" y="55" width="8" height="15" rx="4" fill="{METAL}"/>
  <rect x="31" y="74" width="7" height="9" rx="3" fill="{DARK}"/>
  <rect x="44" y="74" width="7" height="9" rx="3" fill="{DARK}"/>
  <rect x="52" y="57" width="12" height="7" rx="3.5" fill="{METAL}"/>
  <path d="M71 41 L87 47 V60 C87 70 80 77 71 81 C62 77 55 70 55 60 V47 Z"
        fill="url(#sh)" stroke="#e0f2fe" stroke-width="2" stroke-linejoin="round"/>
  <path d="M63.5 60.5 L69 66 L79 55" fill="none" stroke="#fff" stroke-width="3.4"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path class="shine" d="M60 49 L66 47 V71 C63 69 60 65 60 60 Z" fill="#fff"/>
</g>
</svg>"""

# The loader's robot car: spinning wheels, a pulsing antenna light.
CAR_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 44">
<style>
  .wheel{{transform-box:fill-box;transform-origin:center;
          animation:spin .6s linear infinite}}
  .led{{animation:led 1s ease-in-out infinite}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
  @keyframes led{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
  {_REDUCED_MOTION}
</style>
<line x1="24" y1="4" x2="24" y2="12" stroke="{TEAL}" stroke-width="2.4"
      stroke-linecap="round"/>
<circle class="led" cx="24" cy="4" r="3.4" fill="{TEAL}"/>
<rect x="5" y="12" width="38" height="22" rx="7" fill="{METAL}"/>
<rect x="11" y="16" width="26" height="10" rx="4" fill="{TEAL_DEEP}"/>
<circle cx="18" cy="21" r="1.8" fill="{TEAL}"/>
<circle cx="30" cy="21" r="1.8" fill="{TEAL}"/>
<g class="wheel"><circle cx="13" cy="35" r="6.5" fill="{DARK}"/>
  <rect x="12.2" y="29.5" width="1.6" height="11" fill="{METAL_SHADE}"/></g>
<g class="wheel"><circle cx="35" cy="35" r="6.5" fill="{DARK}"/>
  <rect x="34.2" y="29.5" width="1.6" height="11" fill="{METAL_SHADE}"/></g>
</svg>"""


def svg_data_uri(svg: str) -> str:
    """Encode an SVG document as a ``data:`` URI usable in an ``<img src>``."""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def mascot_img(size: int, *, alt: str = "DataMon robot holding a shield") -> str:
    return (
        f'<img src="{svg_data_uri(MASCOT_SVG)}" width="{size}" height="{size}" '
        f'alt="{alt}" style="display:block;border-radius:{size * 0.23:.0f}px;'
        f'box-shadow:0 6px 18px rgba(45,212,191,.28);">'
    )
