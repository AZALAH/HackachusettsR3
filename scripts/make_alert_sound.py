"""Generate the error-alert cue as a WAV, using only numpy + the stdlib.

A short descending two-tone "uh-oh" is a faster, less grating error signal than a
spoken line, and it needs no external audio tooling. Run:

    python scripts/make_alert_sound.py

Writes narration/audio/alert_error.wav. The tour plays an mp3 if one exists,
otherwise this wav, so a user who prefers the spoken cue can drop in
alert_error.mp3 and it wins automatically.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

OUT = Path("narration/audio/alert_error.wav")
SAMPLE_RATE = 44_100


def _tone(freq: float, seconds: float, volume: float = 0.4) -> np.ndarray:
    t = np.linspace(0, seconds, int(SAMPLE_RATE * seconds), endpoint=False)
    wave_data = np.sin(2 * np.pi * freq * t)
    # Short fade in/out so the tone does not click at the edges.
    fade = int(SAMPLE_RATE * 0.01)
    envelope = np.ones_like(wave_data)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    return wave_data * envelope * volume


def main() -> None:
    gap = np.zeros(int(SAMPLE_RATE * 0.05))
    signal = np.concatenate([
        _tone(660.0, 0.14),   # first beep
        gap,
        _tone(440.0, 0.20),   # lower second beep -> "uh-oh"
    ])
    pcm = np.int16(np.clip(signal, -1.0, 1.0) * 32767)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
