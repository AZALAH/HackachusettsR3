"""Simulate a live transport feeding the collector adapter into the gate.

This stands in for a ROS 2 subscription, a WebSocket feed, or an SDK callback:
each would call ``adapter.submit(Frame(...))`` exactly as the loop below does.
It demonstrates the three live-only policies — clean disconnect, a short partial
dropped on disconnect, and backpressure under a burst — without any network.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from datamon.collector import BackpressurePolicy, CollectorAdapter, Frame
from datamon.frames import load_parquet
from datamon.gate import GateConfig, IngestGate
from datamon.lerobot import load_episodes, task_map

DROID_ROOT = Path("data/lerobot/droid_100")
DROID_DATA = DROID_ROOT / "data" / "chunk-000" / "file-000.parquet"


def _submit_episode(adapter: CollectorAdapter, episode, *, limit=None) -> None:
    count = episode.n_frames if limit is None else min(limit, episode.n_frames)
    for position in range(count):
        adapter.submit(Frame(
            episode_index=episode.episode_index,
            frame_index=int(episode.frame_index[position]),
            timestamp=float(episode.timestamp[position]),
            state=episode.state[position],
            action=episode.action[position],
            task=episode.task,
            task_index=episode.task_index,
            source="live-collector",
        ))


def main() -> None:
    if not DROID_DATA.is_file():
        raise SystemExit("Demo data is missing. Run: python scripts/download_frames.py")
    metadata = load_episodes(DROID_ROOT)
    episodes = load_parquet(
        DROID_DATA, fps=15.0, tasks_by_episode=task_map(metadata), source="droid_100",
    )

    with tempfile.TemporaryDirectory(prefix="datamon-collector-") as directory:
        gate = IngestGate(Path(directory), GateConfig()).calibrate(episodes[:60])

        # 1. A full episode arrives and disconnects cleanly -> gated.
        adapter = CollectorAdapter(gate, fps=15.0)
        _submit_episode(adapter, episodes[60])
        result = adapter.disconnect()
        print(f"clean disconnect -> {result.decision.value.upper()} "
              f"(episode {result.episode_index})")

        # 2. Transport drops after two frames -> partial discarded, nothing stored.
        adapter = CollectorAdapter(gate, fps=15.0, min_frames_on_disconnect=5)
        _submit_episode(adapter, episodes[61], limit=2)
        dropped = adapter.disconnect()
        print(f"short partial on disconnect -> stored: {dropped is not None}, "
              f"partials_discarded={adapter.stats.partials_discarded}")

        # 3. A burst overruns a tiny queue -> drop-oldest backpressure counts drops.
        adapter = CollectorAdapter(
            gate, fps=15.0, max_queue=16,
            backpressure=BackpressurePolicy.DROP_OLDEST,
        )
        _submit_episode(adapter, episodes[62])
        adapter.disconnect()
        print(f"backpressure burst -> dropped {adapter.stats.frames_dropped_backpressure} "
              f"frame(s) at the queue, ingested {adapter.stats.frames_ingested}")

        print(f"Gate decisions after live collection: {gate.stats()}")


if __name__ == "__main__":
    main()
