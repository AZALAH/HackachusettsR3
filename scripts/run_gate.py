"""Demonstrate accept/review/quarantine routing on DROID-100."""

from __future__ import annotations

import copy
import tempfile
from pathlib import Path

import numpy as np

from datamon.frames import load_parquet
from datamon.gate import Decision, GateConfig, IngestGate
from datamon.lerobot import load_episodes, task_map
from datamon.stream import StreamIngestor

DROID_ROOT = Path("data/lerobot/droid_100")
DROID_DATA = DROID_ROOT / "data" / "chunk-000" / "file-000.parquet"


def main() -> None:
    if not DROID_DATA.is_file():
        raise SystemExit("Demo data is missing. Run: python scripts/download_frames.py")
    metadata = load_episodes(DROID_ROOT)
    episodes = load_parquet(
        DROID_DATA, fps=15.0, tasks_by_episode=task_map(metadata), source="droid_100",
    )
    print(f"Loaded {len(episodes)} episodes")

    with tempfile.TemporaryDirectory(prefix="datamon-gate-") as directory:
        gate = IngestGate(Path(directory), GateConfig()).calibrate(episodes[:60])
        for episode in episodes[60:]:
            gate.admit(episode)

        dropped = copy.deepcopy(episodes[0])
        dropped.episode_index = 9001
        keep = np.ones(dropped.n_frames, bool)
        keep[dropped.n_frames // 2:dropped.n_frames // 2 + 5] = False
        dropped.timestamp, dropped.frame_index = dropped.timestamp[keep], dropped.frame_index[keep]
        dropped.state, dropped.action = dropped.state[keep], dropped.action[keep]
        gate.admit(dropped)

        invalid = copy.deepcopy(episodes[1])
        invalid.episode_index = 9002
        invalid.state[3, 0] = np.nan
        gate.admit(invalid)

        short = copy.deepcopy(episodes[2])
        short.episode_index = 9003
        short.timestamp, short.frame_index = short.timestamp[:3], short.frame_index[:3]
        short.state, short.action = short.state[:3], short.action[:3]
        gate.admit(short)

        print(f"Gate decisions: {gate.stats()}")
        print(f"Rejected frames kept out of training: {gate.wasted_frames_prevented()}")
        for decision in Decision:
            count = len(list(gate.dirs[decision].rglob("*.parquet")))
            print(f"  {decision.value:8s}: {count} routed episode(s)")

        warnings = []
        ingestor = StreamIngestor(
            gate, fps=15.0,
            on_frame=lambda feedback: warnings.extend(
                (feedback.frame_index, warning) for warning in feedback.warnings
            ),
        )
        result = ingestor.replay_episode(dropped)
        print(f"Streamed episode {result.episode_index}: {result.decision.value.upper()}")
        for frame_index, warning in warnings[:3]:
            print(f"  frame {frame_index}: {warning}")


if __name__ == "__main__":
    main()
