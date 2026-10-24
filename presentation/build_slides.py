"""Build the DataMon pitch deck as an editable .pptx (opens in Google Slides).

    python presentation/build_slides.py

Writes presentation/DataMon.pptx. Uses only the Python standard library, so it
runs anywhere. Every slide is native text and shapes (fully editable after
import), and each slide's speaker notes carry its lines from the video script.

To open in Google Slides: Google Drive -> New -> File upload -> DataMon.pptx,
then right-click the file -> Open with -> Google Slides.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUT = HERE / "DataMon.pptx"

EMU = 914400  # per inch
W, H = 13.333, 7.5  # 16:9 slide, inches

BG = "0E1117"
PANEL = "151C26"
PANEL_LINE = "23414A"
TEAL = "2DD4BF"
TEAL_DEEP = "0D9488"
TEXT = "E6EDF3"
MUTED = "9FB3C8"
GREEN = "2E9E44"
AMBER = "D9A400"
RED = "D64545"
HEAD_FONT = "Montserrat"
BODY_FONT = "Open Sans"

NS = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
)
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
GRP = (
    '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
    '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
)


def emu(inches: float) -> int:
    return int(round(inches * EMU))


def png_size(path: Path) -> tuple:
    data = path.read_bytes()[:24]
    return struct.unpack(">II", data[16:24])


# --- Slide building blocks ---------------------------------------------------

class Slide:
    def __init__(self, notes: str):
        self.shapes = []
        self.images = []  # (rId, filename)
        self.notes = notes
        self._id = 2
        self.page = 0

    def _next(self) -> int:
        self._id += 1
        return self._id

    def text(self, x, y, w, h, paragraphs, *, anchor="t", fill=None, line=None,
             radius=False, inset=0.08):
        """paragraphs: list of dicts {runs:[(text, {opts})], align, bullet, space}."""
        sid = self._next()
        geom = "roundRect" if radius else "rect"
        adj = '<a:gd name="adj" fmla="val 8000"/>' if radius else ""
        fill_xml = (f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
                    if fill else "<a:noFill/>")
        line_xml = (f'<a:ln w="15875"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
                    if line else "<a:ln><a:noFill/></a:ln>")
        ins = emu(inset)
        body = "".join(_paragraph(p) for p in paragraphs)
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Text {sid}"/>'
            f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/>'
            f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geom}"><a:avLst>{adj}</a:avLst></a:prstGeom>'
            f'{fill_xml}{line_xml}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="{ins}" tIns="{ins}" '
            f'rIns="{ins}" bIns="{ins}" anchor="{anchor}"><a:noAutofit/></a:bodyPr>'
            f'<a:lstStyle/>{body}</p:txBody></p:sp>'
        )

    def box(self, x, y, w, h, fill, *, line=None, radius=True):
        sid = self._next()
        geom = "roundRect" if radius else "rect"
        adj = '<a:gd name="adj" fmla="val 10000"/>' if radius else ""
        line_xml = (f'<a:ln w="15875"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
                    if line else "<a:ln><a:noFill/></a:ln>")
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Shape {sid}"/><p:cNvSpPr/>'
            f'<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/>'
            f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geom}"><a:avLst>{adj}</a:avLst></a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{line_xml}</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p>'
            f'</p:txBody></p:sp>'
        )

    def image(self, filename, x, y, *, w=None, h=None):
        path = ASSETS / filename
        pw, ph = png_size(path)
        if w is not None and h is None:
            h = w * ph / pw
        elif h is not None and w is None:
            w = h * pw / ph
        rid = f"rId{len(self.images) + 3}"
        self.images.append((rid, filename))
        sid = self._next()
        self.shapes.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="{escape(filename)}"/>'
            f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch>'
            f'</p:blipFill><p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/>'
            f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        )
        return w, h

    def xml(self) -> str:
        return (
            f'{XML}<p:sld {NS}><p:cSld><p:bg><p:bgPr><a:solidFill>'
            f'<a:srgbClr val="{BG}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
            f'<p:spTree>{GRP}{"".join(self.shapes).replace("__PAGE__", str(self.page))}'
            f'</p:spTree></p:cSld>'
            f'<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
        )


def _run(text, size=18, color=TEXT, bold=False, font=BODY_FONT, italic=False):
    return (text, {"size": size, "color": color, "bold": bold, "font": font,
                   "italic": italic})


def _paragraph(p) -> str:
    align = {"l": "l", "c": "ctr", "r": "r"}[p.get("align", "l")]
    space = p.get("space", 0)
    ppr = f'<a:pPr algn="{align}"'
    inner = ""
    if p.get("bullet"):
        ppr += ' marL="285750" indent="-285750"'
        inner += (f'<a:buClr><a:srgbClr val="{p.get("bullet_color", TEAL)}"/></a:buClr>'
                  '<a:buFont typeface="Arial"/><a:buChar char="&#8226;"/>')
    else:
        inner += "<a:buNone/>"
    if space:
        inner = f'<a:spcBef><a:spcPts val="{int(space * 100)}"/></a:spcBef>' + inner
    ppr += f">{inner}</a:pPr>"
    runs = ""
    last = None
    for text, o in p["runs"]:
        last = o
        runs += (
            f'<a:r><a:rPr lang="en-US" sz="{int(o["size"] * 100)}" '
            f'b="{1 if o["bold"] else 0}" i="{1 if o["italic"] else 0}" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{o["color"]}"/></a:solidFill>'
            f'<a:latin typeface="{o["font"]}"/><a:cs typeface="{o["font"]}"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r>'
        )
    size = int((last or {"size": 18})["size"] * 100)
    return f'<a:p>{ppr}{runs}<a:endParaRPr lang="en-US" sz="{size}" dirty="0"/></a:p>'


def P(*runs, align="l", bullet=False, space=0, bullet_color=TEAL):
    return {"runs": list(runs), "align": align, "bullet": bullet, "space": space,
            "bullet_color": bullet_color}


def title(s: Slide, kicker: str, heading: str, y=0.55):
    s.text(0.75, y, 11.8, 0.4, [P(_run(kicker.upper(), 13, TEAL, True, HEAD_FONT))])
    s.text(0.75, y + 0.38, 11.8, 1.0, [P(_run(heading, 34, TEXT, True, HEAD_FONT))])


def footer(s: Slide, n: int):
    s.box(0.75, 7.02, 0.55, 0.05, TEAL, radius=False)
    s.text(1.4, 6.86, 6, 0.35, [P(_run("DataMon  ·  Hackachusetts  ·  Robotics & Hardware",
                                       10, MUTED))])
    s.text(11.6, 6.86, 1.0, 0.35, [P(_run("__PAGE__", 10, MUTED), align="r")])


def card(s: Slide, x, y, w, h, label, body, accent=TEAL, label_size=18, body_size=13.5):
    s.box(x, y, w, h, PANEL, line=PANEL_LINE)
    s.box(x, y + 0.18, 0.07, h - 0.36, accent, radius=False)
    s.text(x + 0.25, y + 0.15, w - 0.4, 0.5, [P(_run(label, label_size, accent, True,
                                                     HEAD_FONT))])
    paras = body if isinstance(body, list) else [P(_run(body, body_size, TEXT))]
    s.text(x + 0.25, y + 0.62, w - 0.4, h - 0.75, paras)


# --- The deck ------------------------------------------------------------------

def build_slides() -> list:
    slides = []

    # 1. Title
    s = Slide(
        "[0:00-0:10] Hi, I'm Ahmed Salah. My teammate Jesse Silva and I built "
        'DataMon for the Robotics and Hardware track.'
    )
    s.image("mascot.png", 0.85, 1.55, w=2.6)
    s.text(3.85, 1.55, 8.8, 1.3, [P(_run("Data", 66, TEXT, True, HEAD_FONT),
                                    _run("Mon", 66, TEAL, True, HEAD_FONT))])
    s.text(3.9, 2.85, 8.6, 0.9, [P(_run("A quality gate for robot training data.", 26, TEXT))])
    s.text(3.9, 3.5, 8.6, 0.6, [P(_run("Bad demonstrations stop here.", 20, MUTED,
                                       italic=True))])
    for i, chip in enumerate(["ROBOTICS & HARDWARE TRACK", "HACKACHUSETTS", "BUILT WITH KIRO"]):
        cw = 3.05 if i == 0 else (2.25 if i == 1 else 2.25)
        cx = 3.9 + [0, 3.2, 5.6][i]
        s.text(cx, 4.35, cw, 0.42, [P(_run(chip, 11, TEAL, True, HEAD_FONT), align="c")],
               anchor="ctr", fill="10262A", line=TEAL_DEEP, radius=True, inset=0.04)
    s.text(0.85, 5.75, 11.6, 0.5, [P(_run("Team:  ", 15, MUTED, True),
                                     _run("Ahmed Salah  ·  Jesse Silva", 15, TEXT))])
    s.text(0.85, 6.2, 11.6, 0.5, [P(_run("hackachusetts-datamon.streamlit.app", 15, TEAL))])
    s.image("car.png", 11.4, 6.25, w=0.9)
    slides.append(s)

    # 2. Problem
    s = Slide(
        '[0:10-0:20] Robots learn by copying recorded demonstrations. But a frozen '
        'sensor, a timing glitch, or a recording nobody labelled teaches the robot '
        'the wrong thing, and nobody notices until after an expensive training run.'
    )
    title(s, "The problem", "Bad robot data fails silently")
    items = [
        ("Sensor & timing faults", "Frozen readings, dropped frames, glitchy timestamps "
                                   "and impossible values slip into datasets.", RED),
        ("Missing or nonsense labels", "A demonstration the robot was never told the "
                                       "point of teaches it nothing useful.", AMBER),
        ("Found too late", "Problems usually surface after an expensive training run, "
                           "when the data is hardest to fix or recollect.", TEAL),
    ]
    for i, (label, body, accent) in enumerate(items):
        card(s, 0.75 + i * 4.0, 2.2, 3.75, 2.6, label, body, accent)
    s.text(0.75, 5.25, 11.8, 1.2, [P(
        _run("Garbage in, garbage out.  ", 22, TEXT, True, HEAD_FONT),
        _run("Except here, the garbage learns to drive a robot arm.", 20, MUTED,
             italic=True))])
    footer(s, 2)
    slides.append(s)

    # 3. Solution
    s = Slide(
        '[0:20-0:30] DataMon is a quality gate. Every recording gets a score from '
        'zero to a hundred, with reasons, and is accepted, held for a human, or '
        'quarantined. (Next: Kiro slide, then switch to the live demo.)'
    )
    title(s, "The solution", "Every recording is scored, explained and routed")
    s.text(0.75, 1.85, 11.8, 0.6, [P(_run(
        "One score from 0 to 100, with the reasons behind it. The thresholds are yours to set.",
        17, MUTED))])
    routes = [
        ("ACCEPT", "Clean staging store", "Ready for training.", GREEN),
        ("REVIEW", "Held for a human", "The gate isn't sure, so it asks.", AMBER),
        ("REJECT", "Quarantined", "Integrity failures never reach training.", RED),
    ]
    for i, (label, where, why, accent) in enumerate(routes):
        x = 0.75 + i * 4.0
        s.box(x, 2.75, 3.75, 2.9, PANEL, line=accent)
        s.text(x, 2.95, 3.75, 0.7, [P(_run(label, 30, accent, True, HEAD_FONT), align="c")])
        s.text(x + 0.2, 3.8, 3.35, 0.5, [P(_run(where, 18, TEXT, True), align="c")])
        s.text(x + 0.2, 4.35, 3.35, 1.0, [P(_run(why, 14, MUTED), align="c")])
    s.text(0.75, 5.95, 11.8, 0.6, [P(
        _run("Every decision is written to an append-only audit log, keyed by the "
             "recording's content ID.", 15, TEXT))])
    footer(s, 3)
    slides.append(s)

    # 4. How it scores
    s = Slide(
        '(BACKUP SLIDE, not in the video.) Four checks: integrity, labels, an '
        'unusualness rank against known-good recordings, then routing with an audit'
        ' trail. The anomaly number is a rank, not a probability.'
    )
    title(s, "How it works", "Four checks, in plain terms")
    steps = [
        ("1  Integrity", "Is the timing steady? Any dropped frames, frozen channels or "
                         "values out of range?"),
        ("2  Labels", "Was the robot told what it was doing? Missing or gibberish task "
                      "text is flagged."),
        ("3  Unusualness", "How different is it from known-good recordings of the same "
                           "task? A rank, not a probability."),
        ("4  Route + log", "Accept, review or reject, and record why. History is never "
                           "overwritten."),
    ]
    for i, (label, body) in enumerate(steps):
        card(s, 0.75 + i * 3.0, 2.2, 2.8, 2.35, label, body, TEAL, label_size=17,
             body_size=13)
    s.text(0.75, 4.95, 11.8, 0.9, [P(
        _run("Works live too: ", 15, TEAL, True),
        _run("a collector adapter streams frames from a running robot into the same gate, "
             "and per-robot profiles store each rig's expected rate and limits.", 15, TEXT))])
    footer(s, 4)
    slides.append(s)

    # 5. Live demo divider
    s = Slide(
        '(BACKUP SLIDE, not in the video.) Live site and judge sign-in, for a live '
        'presentation or questions.'
    )
    s.text(0.75, 1.6, 11.8, 0.5, [P(_run("LIVE DEMO", 16, TEAL, True, HEAD_FONT),
                                    align="c")])
    s.text(0.75, 2.1, 11.8, 1.2, [P(_run("See it working", 48, TEXT, True, HEAD_FONT),
                                    align="c")])
    s.text(2.9, 3.6, 7.5, 1.6, [
        P(_run("hackachusetts-datamon.streamlit.app", 22, TEAL, True), align="c"),
        P(_run("Sign in:  judge  /  Hello World!", 18, TEXT), align="c", space=10),
    ], anchor="ctr", fill=PANEL, line=PANEL_LINE, radius=True)
    s.text(0.75, 5.6, 11.8, 0.6, [P(_run(
        "Real public data: 100 DROID recordings and a BridgeData V2 sample, "
        "in the open LeRobot format.", 15, MUTED), align="c")])
    footer(s, 5)
    slides.append(s)

    # 6. Accessibility and design
    s = Slide(
        '(BACKUP SLIDE, not in the video.) Narrated tour with captions and a '
        'pointing arrow, a grounded help assistant, a sound plus a colour-coded '
        'verdict on rejections, and reduced-motion support.'
    )
    title(s, "Built for everyone", "Accessible, and fun to use")
    feats = [
        ("Narrated guided tour", "11 steps. Voice, captions and a pointing arrow, so "
                                 "it works with or without sound."),
        ("Grounded help assistant", "Answers only from DataMon's own docs, so it "
                                    "never invents an answer."),
        ("See it and hear it", "Rejections show a colour-coded verdict and play an "
                               "alert sound."),
        ("Reduced motion", "Every animation switches off for people who turn off "
                           "motion in their system settings."),
    ]
    for i, (label, body) in enumerate(feats):
        y = 1.95 + i * 1.18
        s.text(0.75, y, 6.3, 0.45, [P(_run(label, 18, TEAL, True, HEAD_FONT))])
        s.text(0.75, y + 0.42, 6.3, 0.7, [P(_run(body, 13.5, TEXT))])
    s.image("loader.png", 7.35, 1.95, w=5.25)
    s.text(7.35, 5.35, 5.25, 0.9, [P(_run(
        "The loading screen does real work (it loads and scores the data) and passes "
        "the time with robotics jokes and fun facts.", 12, MUTED, italic=True))])
    footer(s, 6)
    slides.append(s)

    # 7. How we used Kiro
    s = Slide(
        '[0:30-0:52] We built it entirely with Kiro. Kiro Crew on my laptop set up '
        'the project, ran the tests, and shipped every feature as its own pull '
        "request. Kiro Web, in the cloud, couldn't install Streamlit, so it read "
        "Streamlit's source on GitHub and used the Playwright power to screenshot "
        'the UI before shipping. Specs and steering docs kept it consistent: '
        'twenty-one pull requests, a hundred and twenty-nine passing tests. (Then '
        'switch to the live demo: see VIDEO_SCRIPT.md, 0:52-2:42.)'
    )
    title(s, "Implementation", "How we used Kiro")
    s.box(0.75, 1.95, 5.75, 2.2, PANEL, line=PANEL_LINE)
    s.text(1.0, 2.05, 5.3, 0.5, [P(_run("Kiro Crew  ·  local laptop", 18, TEAL, True,
                                        HEAD_FONT))])
    s.text(1.0, 2.55, 5.3, 1.9, [
        P(_run("Set up Python and the virtual environment", 13.5, TEXT), bullet=True),
        P(_run("Ran the app and the tests on the real machine", 13.5, TEXT), bullet=True,
          space=4),
        P(_run("Shipped every feature as its own branch, pull request and merge", 13.5, TEXT),
          bullet=True, space=4),
    ])
    s.box(6.85, 1.95, 5.75, 2.2, PANEL, line=PANEL_LINE)
    s.text(7.1, 2.05, 5.3, 0.5, [P(_run("Kiro Web  ·  cloud sandbox", 18, TEAL, True,
                                        HEAD_FONT))])
    s.text(7.1, 2.55, 5.3, 1.9, [
        P(_run("No internet to install Streamlit, so it read the library's source "
               "on GitHub", 13.5, TEXT), bullet=True),
        P(_run("Playwright power (MCP) rendered and screenshotted the UI", 13.5, TEXT),
          bullet=True, space=4),
        P(_run("GitHub CI ran the full test suite on every pull request", 13.5, TEXT),
          bullet=True, space=4),
    ])
    stats = [("Specs", "requirements, design and tasks for core features"),
             ("Steering", "2 docs: test before merge, no overclaiming"),
             ("21", "merged pull requests"),
             ("129", "tests passing on Python 3.9 & 3.13")]
    for i, (big, small) in enumerate(stats):
        x = 0.75 + i * 3.0
        s.text(x, 4.55, 2.8, 0.6, [P(_run(big, 28, TEAL, True, HEAD_FONT))])
        s.text(x, 5.15, 2.8, 0.8, [P(_run(small, 13, TEXT))])
    s.text(0.75, 6.05, 11.8, 0.5, [P(_run(
        "Full write-up and specs: the /.kiro folder in our repo.", 12.5, MUTED,
        italic=True))])
    footer(s, 7)
    slides.append(s)

    # 8. Who benefits / scale
    s = Slide(
        '(BACKUP SLIDE, not in the video.) Labs, data-collection teams and dataset '
        'publishers. Reads any LeRobot dataset, streams from live robots, per-robot'
        ' profiles and per-task baselines.'
    )
    title(s, "Potential value", "Who benefits, and how it scales")
    who = [
        ("Robotics labs", "Stop wasting training runs on broken demonstrations."),
        ("Data-collection teams", "Catch a bad recording while the robot and operator "
                                  "are still there to redo it."),
        ("Dataset publishers", "Ship a quality report and an audit trail with every "
                               "release."),
    ]
    for i, (label, body) in enumerate(who):
        card(s, 0.75 + i * 4.0, 2.05, 3.75, 1.95, label, body, TEAL)
    s.text(0.75, 4.35, 11.8, 0.5, [P(_run("Built to scale", 18, TEAL, True, HEAD_FONT))])
    s.text(0.75, 4.85, 11.8, 1.8, [
        P(_run("Reads the open LeRobot format, so any dataset published that way works "
               "with no conversion", 14, TEXT), bullet=True),
        P(_run("Streams from a live robot through a transport-agnostic collector "
               "adapter (ROS 2, WebSocket, robot SDKs)", 14, TEXT), bullet=True, space=5),
        P(_run("Per-robot profiles and per-task baselines, so new rigs and tasks "
               "slot in", 14, TEXT), bullet=True, space=5),
    ])
    footer(s, 8)
    slides.append(s)

    # 9. Try it
    s = Slide(
        '[2:42-2:55] It reads the open LeRobot format, so it works with any dataset'
        " published that way. Good data in, bad data out. That's DataMon. Thanks "
        'for watching.'
    )
    s.image("mascot.png", 0.85, 1.0, w=1.6)
    s.text(2.7, 1.05, 5.0, 1.0, [P(_run("Try DataMon", 40, TEXT, True, HEAD_FONT))])
    s.text(2.7, 1.85, 5.0, 0.6, [P(_run("Good data in. Bad data out.", 20, TEAL,
                                        italic=True))])
    s.text(0.85, 3.0, 6.3, 2.7, [
        P(_run("LIVE SITE", 12, MUTED, True, HEAD_FONT)),
        P(_run("hackachusetts-datamon.streamlit.app", 17, TEAL, True), space=2),
        P(_run("SIGN IN", 12, MUTED, True, HEAD_FONT), space=14),
        P(_run("judge  /  Hello World!", 17, TEXT, True), space=2),
        P(_run("CODE + KIRO SPECS", 12, MUTED, True, HEAD_FONT), space=14),
        P(_run("github.com/AZALAH/HackachusettsR3", 17, TEAL, True), space=2),
    ], fill=PANEL, line=PANEL_LINE, radius=True, inset=0.25)
    s.image("login.png", 7.45, 1.05, w=5.15)
    s.text(7.45, 4.45, 5.15, 0.5, [P(_run("The DataMon sign-in page", 12, MUTED,
                                          italic=True), align="c")])
    s.text(7.45, 5.3, 5.15, 0.9, [P(_run("Thank you!", 30, TEXT, True, HEAD_FONT),
                                    align="c")])
    footer(s, 9)
    slides.append(s)
    # Video order: title, problem, solution, Kiro, close. Then backup slides
    # for questions: how scoring works, accessibility, who benefits, demo card.
    title_, problem, solution, how, demo, access, kiro, value, close = slides
    ordered = [title_, problem, solution, kiro, close, how, access, value, demo]
    for page, slide in enumerate(ordered, start=1):
        slide.page = page
    return ordered


# --- Package parts ---------------------------------------------------------------

THEME = (
    f'{XML}<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'name="DataMon"><a:themeElements><a:clrScheme name="DataMon">'
    f'<a:dk1><a:srgbClr val="{BG}"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
    '<a:dk2><a:srgbClr val="1A1F2B"/></a:dk2><a:lt2><a:srgbClr val="E6EDF3"/></a:lt2>'
    f'<a:accent1><a:srgbClr val="{TEAL}"/></a:accent1>'
    f'<a:accent2><a:srgbClr val="{TEAL_DEEP}"/></a:accent2>'
    '<a:accent3><a:srgbClr val="38BDF8"/></a:accent3>'
    f'<a:accent4><a:srgbClr val="{GREEN}"/></a:accent4>'
    f'<a:accent5><a:srgbClr val="{AMBER}"/></a:accent5>'
    f'<a:accent6><a:srgbClr val="{RED}"/></a:accent6>'
    '<a:hlink><a:srgbClr val="2DD4BF"/></a:hlink>'
    '<a:folHlink><a:srgbClr val="99F6E4"/></a:folHlink></a:clrScheme>'
    f'<a:fontScheme name="DataMon"><a:majorFont><a:latin typeface="{HEAD_FONT}"/>'
    '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
    f'<a:minorFont><a:latin typeface="{BODY_FONT}"/><a:ea typeface=""/>'
    '<a:cs typeface=""/></a:minorFont></a:fontScheme>'
    '<a:fmtScheme name="DataMon"><a:fillStyleLst>'
    + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3
    + '</a:fillStyleLst><a:lnStyleLst>'
    + '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>' * 3
    + '</a:lnStyleLst><a:effectStyleLst>'
    + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3
    + '</a:effectStyleLst><a:bgFillStyleLst>'
    + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3
    + '</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'
)

CLRMAP = ('<p:clrMap bg1="dk1" tx1="lt1" bg2="dk2" tx2="lt2" accent1="accent1" '
          'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
          'accent6="accent6" hlink="hlink" folHlink="folHlink"/>')

MASTER = (
    f'{XML}<p:sldMaster {NS}><p:cSld><p:bg><p:bgPr><a:solidFill>'
    f'<a:srgbClr val="{BG}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
    f'<p:spTree>{GRP}</p:spTree></p:cSld>{CLRMAP}'
    '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
    '</p:sldMaster>'
)

LAYOUT = (
    f'{XML}<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank">'
    f'<p:spTree>{GRP}</p:spTree></p:cSld>'
    '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
)


_EMPTY_PARA = '<a:p><a:endParaRPr lang="en-US"/></a:p>'


def _notes_placeholder(sid, ph, x, y, w, h, body=""):
    body = body or _EMPTY_PARA
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{ph} {sid}"/><p:cNvSpPr/>'
        f'<p:nvPr><p:ph type="{ph}" idx="{1 if ph == "body" else 2}"/></p:nvPr></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/>{body}'
        f'</p:txBody></p:sp>'
    )


NOTES_MASTER = (
    f'{XML}<p:notesMaster {NS}><p:cSld><p:spTree>{GRP}'
    + _notes_placeholder(2, "sldImg", 381000, 685800, 6096000, 3429000)
    + _notes_placeholder(3, "body", 685800, 4343400, 5486400, 4114800)
    + f'</p:spTree></p:cSld>{CLRMAP}</p:notesMaster>'
)


def notes_xml(text: str) -> str:
    body = (f'<a:p><a:r><a:rPr lang="en-US" sz="1400" dirty="0"/>'
            f'<a:t>{escape(text)}</a:t></a:r></a:p>')
    return (
        f'{XML}<p:notes {NS}><p:cSld><p:spTree>{GRP}'
        + _notes_placeholder(2, "body", 685800, 4343400, 5486400, 4114800, body)
        + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
    )


def rels(entries) -> str:
    items = "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/{kind}" Target="{target}"/>'
        for rid, kind, target in entries
    )
    return (f'{XML}<Relationships xmlns="http://schemas.openxmlformats.org/'
            f'package/2006/relationships">{items}</Relationships>')


def build(out: Path = OUT) -> Path:
    slides = build_slides()
    n = len(slides)
    ct = "application/vnd.openxmlformats-officedocument.presentationml"
    overrides = [
        ("/ppt/presentation.xml", f"{ct}.presentation.main+xml"),
        ("/ppt/slideMasters/slideMaster1.xml", f"{ct}.slideMaster+xml"),
        ("/ppt/slideLayouts/slideLayout1.xml", f"{ct}.slideLayout+xml"),
        ("/ppt/notesMasters/notesMaster1.xml", f"{ct}.notesMaster+xml"),
        ("/ppt/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
        ("/ppt/theme/theme2.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
        ("/ppt/presProps.xml", f"{ct}.presProps+xml"),
        ("/ppt/viewProps.xml", f"{ct}.viewProps+xml"),
        ("/ppt/tableStyles.xml", f"{ct}.tableStyles+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
        ("/docProps/app.xml",
         "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
    ]
    for i in range(1, n + 1):
        overrides.append((f"/ppt/slides/slide{i}.xml", f"{ct}.slide+xml"))
        overrides.append((f"/ppt/notesSlides/notesSlide{i}.xml", f"{ct}.notesSlide+xml"))
    content_types = (
        f'{XML}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
        'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        + "".join(f'<Override PartName="{p}" ContentType="{c}"/>' for p, c in overrides)
        + "</Types>"
    )
    sld_ids = "".join(f'<p:sldId id="{256 + i}" r:id="rId{10 + i}"/>' for i in range(n))
    presentation = (
        f'{XML}<p:presentation {NS} saveSubsetFonts="1">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        '<p:notesMasterIdLst><p:notesMasterId r:id="rId2"/></p:notesMasterIdLst>'
        f'<p:sldIdLst>{sld_ids}</p:sldIdLst>'
        f'<p:sldSz cx="{emu(W)}" cy="{emu(H)}"/><p:notesSz cx="6858000" cy="9144000"/>'
        '</p:presentation>'
    )
    pres_rels = [
        ("rId1", "slideMaster", "slideMasters/slideMaster1.xml"),
        ("rId2", "notesMaster", "notesMasters/notesMaster1.xml"),
        ("rId3", "theme", "theme/theme1.xml"),
        ("rId4", "presProps", "presProps.xml"),
        ("rId5", "viewProps", "viewProps.xml"),
        ("rId6", "tableStyles", "tableStyles.xml"),
    ] + [(f"rId{10 + i}", "slide", f"slides/slide{i + 1}.xml") for i in range(n)]

    pkg = "http://schemas.openxmlformats.org"
    core = (
        f'{XML}<cp:coreProperties xmlns:cp="{pkg}/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>DataMon: a quality gate for robot training data</dc:title>'
        '<dc:creator>Ahmed Salah, Jesse Silva</dc:creator></cp:coreProperties>'
    )
    app = (f'{XML}<Properties xmlns="{pkg}/officeDocument/2006/extended-properties">'
           f'<Application>DataMon build_slides.py</Application><Slides>{n}</Slides></Properties>')

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels([
            ("rId1", "officeDocument", "ppt/presentation.xml"),
            ("rId2", "metadata/core-properties", "docProps/core.xml"),
            ("rId3", "extended-properties", "docProps/app.xml"),
        ]).replace(f"{pkg}/officeDocument/2006/relationships/metadata/core-properties",
                   f"{pkg}/package/2006/relationships/metadata/core-properties"))
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", rels(pres_rels))
        z.writestr("ppt/presProps.xml", f"{XML}<p:presentationPr {NS}/>")
        z.writestr("ppt/viewProps.xml", f"{XML}<p:viewPr {NS}/>")
        z.writestr("ppt/tableStyles.xml",
                   f'{XML}<a:tblStyleLst xmlns:a="{pkg}/drawingml/2006/main" '
                   'def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>')
        z.writestr("ppt/theme/theme1.xml", THEME)
        z.writestr("ppt/theme/theme2.xml", THEME)
        z.writestr("ppt/slideMasters/slideMaster1.xml", MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels([
            ("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", "theme", "../theme/theme1.xml"),
        ]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels([
            ("rId1", "slideMaster", "../slideMasters/slideMaster1.xml"),
        ]))
        z.writestr("ppt/notesMasters/notesMaster1.xml", NOTES_MASTER)
        z.writestr("ppt/notesMasters/_rels/notesMaster1.xml.rels", rels([
            ("rId1", "theme", "../theme/theme2.xml"),
        ]))
        media = {}
        for i, slide in enumerate(slides, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide.xml())
            entries = [
                ("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"),
                ("rId2", "notesSlide", f"../notesSlides/notesSlide{i}.xml"),
            ]
            for rid, filename in slide.images:
                if filename not in media:
                    media[filename] = f"image{len(media) + 1}.png"
                    z.write(ASSETS / filename, f"ppt/media/{media[filename]}")
                entries.append((rid, "image", f"../media/{media[filename]}"))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", rels(entries))
            z.writestr(f"ppt/notesSlides/notesSlide{i}.xml", notes_xml(slide.notes))
            z.writestr(f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels", rels([
                ("rId1", "notesMaster", "../notesMasters/notesMaster1.xml"),
                ("rId2", "slide", f"../slides/slide{i}.xml"),
            ]))
    return out


if __name__ == "__main__":
    path = build()
    print(f"wrote {path} ({path.stat().st_size / 1e3:.0f} KB)")
