"""Run frame checks on real and deliberately corrupted episodes."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

from datamon.frame_quality import analyze_frames
from datamon.frames import load_episode_file, load_parquet

BRIDGE = Path("data/lerobot/bridge_v2/data/chunk-000")
DROID = Path("data/lerobot/droid_100/data/chunk-000/file-000.parquet")


def show(tag, report) -> None:
    print(f"  [{tag}] {report.n_frames} frames -> {report.counts_by_check() or 'clean'}")
    for flag in report.flags:
        print(f"      {flag.severity.value:5s} {flag.check}: {flag.reason}")


def main() -> None:
    if not DROID.is_file() or not (BRIDGE / "episode_000000.parquet").is_file():
        raise SystemExit("Demo data is missing. Run: python scripts/download_frames.py")
    clean = load_episode_file(
        BRIDGE / "episode_000000.parquet", fps=5.0, source="bridge_v2",
    )
    droid = load_parquet(DROID, fps=15.0, source="droid_100")
    print("Real episodes")
    show("Bridge episode 0", analyze_frames(clean))
    show("DROID episode 0", analyze_frames(droid[0]))

    print("\nInjected faults")
    dropped = copy.deepcopy(clean)
    keep = np.ones(dropped.n_frames, dtype=bool)
    keep[10:13] = False
    dropped.frame_index = dropped.frame_index[keep]
    dropped.timestamp = dropped.timestamp[keep]
    dropped.state = dropped.state[keep]
    dropped.action = dropped.action[keep]
    show("dropped 3 frames", analyze_frames(dropped))

    drift = copy.deepcopy(clean)
    drift.timestamp = np.cumsum(np.linspace(0.2, 0.35, drift.n_frames))
    show("timing drift", analyze_frames(drift))

    stuck = copy.deepcopy(clean)
    stuck.state[:8, 0] = np.linspace(-1.0, 1.0, 8)
    stuck.state[8:, 0] = 0.25
    show("stuck state_0", analyze_frames(stuck))

    noisy = copy.deepcopy(clean)
    rng = np.random.default_rng(0)
    noisy.state[:, 1] += rng.normal(
        0, np.ptp(noisy.state[:, 1]) * 2 + 0.5, noisy.n_frames,
    )
    show("noisy state_1", analyze_frames(noisy))

    invalid = copy.deepcopy(clean)
    invalid.action[5, 2] = np.nan
    show("NaN in action_2", analyze_frames(invalid))

    clipped = copy.deepcopy(clean)
    ceiling = np.percentile(clipped.action[:, 0], 40)
    clipped.action[:, 0] = np.minimum(clipped.action[:, 0], ceiling)
    show("clipped action_0", analyze_frames(clipped))


if __name__ == "__main__":
    main()
