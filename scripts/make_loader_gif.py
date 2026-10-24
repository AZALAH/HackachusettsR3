"""Render the DataMon loading animation as a looping GIF.

Streamlit re-runs and re-renders on every interaction, which restarts (and
visually freezes) CSS keyframe animations. A GIF sidesteps that entirely: it is
an image that plays itself, so it animates reliably in Streamlit exactly as it
would on a static GitHub page. Run once and commit the asset:

    python scripts/make_loader_gif.py

Writes assets/loader.gif. Uses Pillow (dev/runtime dependency) at BUILD time
only; the app just displays the committed GIF, so the hosted app needs nothing.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("assets/loader.gif")
WIDTH, HEIGHT = 620, 230
FRAMES = 60          # ~3s loop at 50ms/frame; loops to cover the 9s hold
FRAME_MS = 50

BG = (14, 17, 23)
PANEL = (19, 48, 58)
TEAL = (45, 212, 191)
TEAL_DEEP = (13, 148, 136)
TEXT = (230, 237, 243)
SUB = (159, 179, 200)


def _font(size: int):
    for name in ("segoeuib.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _robot(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    # A tiny robot car: body, window, two wheels, an antenna.
    body = (x, y, x + 34, y + 22)
    draw.rounded_rectangle(body, radius=6, fill=(210, 230, 235))
    draw.rounded_rectangle((x + 6, y + 4, x + 28, y + 13), radius=3, fill=TEAL_DEEP)
    draw.ellipse((x + 4, y + 20, x + 14, y + 30), fill=(40, 40, 50))
    draw.ellipse((x + 22, y + 20, x + 32, y + 30), fill=(40, 40, 50))
    draw.line((x + 17, y, x + 17, y - 8), fill=TEAL, width=2)
    draw.ellipse((x + 14, y - 12, x + 20, y - 6), fill=TEAL)


def main() -> None:
    big, small = _font(40), _font(20)
    track_x0, track_x1 = 40, WIDTH - 40
    track_y = 140
    track_h = 28
    frames = []
    for i in range(FRAMES):
        t = i / (FRAMES - 1)
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(img)

        # Title + subtitle.
        d.text((WIDTH // 2, 36), "Welcome to DataMon", font=big, fill=TEXT, anchor="mm")
        d.text((WIDTH // 2, 74), "Starting the quality monitor…", font=small,
               fill=SUB, anchor="mm")

        # Track + fill.
        d.rounded_rectangle((track_x0, track_y, track_x1, track_y + track_h),
                            radius=14, fill=PANEL, outline=TEAL)
        fill_x = int(track_x0 + (track_x1 - track_x0) * t)
        if fill_x > track_x0 + 2:
            d.rounded_rectangle((track_x0, track_y, fill_x, track_y + track_h),
                                radius=14, fill=TEAL_DEEP)

        # Robot bobbing along the top of the bar.
        bob = -3 if (i // 4) % 2 == 0 else 0
        robot_x = int(track_x0 + (track_x1 - track_x0 - 34) * t)
        _robot(d, robot_x, track_y - 34 + bob)

        # Percentage.
        d.text((WIDTH // 2, track_y + track_h + 28), f"{int(t * 100)}%",
               font=small, fill=TEAL, anchor="mm")
        frames.append(img)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT, save_all=True, append_images=frames[1:],
        duration=FRAME_MS, loop=0, optimize=True,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {FRAMES} frames)")


if __name__ == "__main__":
    main()
