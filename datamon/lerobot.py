"""Load compact LeRobot dataset metadata without downloading videos."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

DEFAULT_ROOT = Path("data/lerobot/bridge_v2")


@dataclass(frozen=True)
class DatasetInfo:
    fps: float
    robot_type: str
    total_episodes: int
    total_frames: int
    features: List[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict, compare=False)

    @property
    def frame_interval(self) -> float:
        return 1.0 / self.fps


def load_info(root: Path = DEFAULT_ROOT) -> DatasetInfo:
    path = Path(root) / "meta" / "info.json"
    if not path.is_file():
        raise FileNotFoundError(f"LeRobot metadata not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    required = ("fps", "total_episodes", "total_frames", "features")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"{path} is missing required fields: {missing}")
    fps = float(raw["fps"])
    total_episodes = int(raw["total_episodes"])
    total_frames = int(raw["total_frames"])
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError(f"{path} has invalid fps: {raw['fps']!r}")
    if total_episodes < 0 or total_frames < 0:
        raise ValueError(f"{path} has negative dataset totals")
    if not isinstance(raw["features"], dict):
        raise ValueError(f"{path} features must be an object")

    return DatasetInfo(
        fps=fps,
        robot_type=str(raw.get("robot_type") or "unknown"),
        total_episodes=total_episodes,
        total_frames=total_frames,
        features=list(raw["features"].keys()),
        raw=raw,
    )


def _tasks_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if not isinstance(value, (list, tuple)):
        value = [value]
    return [str(item).strip() for item in value if item is not None and str(item).strip()]


def _normalize_episode_rows(rows: List[dict]) -> pd.DataFrame:
    normalized = []
    for fallback_index, obj in enumerate(rows):
        tasks = _tasks_list(obj.get("tasks"))
        normalized.append({
            "episode_index": int(obj.get("episode_index", fallback_index)),
            "length": obj.get("length"),
            "n_tasks": len(tasks),
            "task": tasks[0] if tasks else "",
            "tasks": tasks,
        })
    return pd.DataFrame(
        normalized,
        columns=["episode_index", "length", "n_tasks", "task", "tasks"],
    )


def load_episodes(root: Path = DEFAULT_ROOT, limit: Optional[int] = None) -> pd.DataFrame:
    """Read LeRobot v2 JSONL or v3 chunked-parquet episode metadata."""
    root = Path(root)
    jsonl = root / "meta" / "episodes.jsonl"
    rows: List[dict] = []

    if jsonl.is_file():
        with jsonl.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
        return _normalize_episode_rows(rows)

    parquet_files = sorted((root / "meta" / "episodes").glob("chunk-*/file-*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(
            f"no episodes.jsonl or chunked episode parquet found under {root / 'meta'}"
        )
    remaining = limit
    frames = []
    for path in parquet_files:
        part = pd.read_parquet(path, columns=["episode_index", "tasks", "length"])
        if remaining is not None:
            part = part.head(remaining)
            remaining -= len(part)
        frames.append(part)
        if remaining == 0:
            break
    rows = pd.concat(frames, ignore_index=True).to_dict(orient="records")
    return _normalize_episode_rows(rows)


def task_map(episodes: pd.DataFrame) -> Dict[int, str]:
    """Map episode index to its first non-empty task description."""
    mapping: Dict[int, str] = {}
    for row in episodes.itertuples(index=False):
        task = str(row.task or "").strip()
        if task:
            mapping[int(row.episode_index)] = task
    return mapping
