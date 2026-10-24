"""Score real DROID-100 episodes and show an injected integrity failure."""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path

import numpy as np

from datamon.frame_quality import analyze_frames
from datamon.lerobot import load_episodes, task_map
from datamon.monitor import Monitor
from datamon.scoring import score_episode

DROID_ROOT = Path("data/lerobot/droid_100")
DROID_DATA = DROID_ROOT / "data" / "chunk-000" / "file-000.parquet"


def main() -> None:
    if not DROID_DATA.is_file():
        raise SystemExit("Demo data is missing. Run: python scripts/download_frames.py")
    metadata = load_episodes(DROID_ROOT)
    monitor = Monitor.from_parquet(
        DROID_DATA,
        fps=15.0,
        tasks_by_episode=task_map(metadata),
        source="droid_100",
    ).fit()
    results = monitor.analyze_all()
    print(f"Loaded and scored {len(results)} DROID episodes")
    grades = Counter(result.score.grade for result in results)
    print(f"Grade distribution: {dict(grades)}")
    print(f"Mean score: {np.mean([result.score.score for result in results]):.1f}")

    ordered = sorted(results, key=lambda result: result.score.score)
    print("\nWorst 5 episodes")
    for result in ordered[:5]:
        score = result.score
        anomaly = "N/A" if score.anomaly_score is None else f"{score.anomaly_score:.2f}"
        print(
            f"  ep {score.episode_index:>3} score={score.score:5.1f} "
            f"({score.grade}) rule={score.rule_score:.0f} anomaly={anomaly}"
        )
        for reason in score.reasons[:3]:
            print(f"      - {reason}")

    best = max(results, key=lambda result: result.score.score)
    corrupted = copy.deepcopy(best.episode)
    keep = np.ones(corrupted.n_frames, dtype=bool)
    midpoint = corrupted.n_frames // 2
    keep[midpoint:midpoint + 4] = False
    corrupted.timestamp = corrupted.timestamp[keep]
    corrupted.frame_index = corrupted.frame_index[keep]
    corrupted.state = corrupted.state[keep]
    corrupted.action = corrupted.action[keep]
    after = score_episode(
        corrupted.episode_index,
        frame_report=analyze_frames(corrupted),
    )
    print("\nInjected dropped-frame comparison")
    print(f"  before: {best.score.score:.1f} ({best.score.grade})")
    print(f"  after:  {after.score:.1f} ({after.grade})")
    for reason in after.reasons[:2]:
        print(f"      - {reason}")


if __name__ == "__main__":
    main()
