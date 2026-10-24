"""Load bounded LeRobot frame data from parquet into validated episodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REQUIRED_FRAME_COLUMNS = {
    "observation.state",
    "action",
    "timestamp",
    "frame_index",
    "episode_index",
}
DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_ROWS = 1_000_000


@dataclass
class Episode:
    """One robot demonstration and the metadata needed by the quality gate."""

    episode_index: int
    timestamp: np.ndarray
    frame_index: np.ndarray
    state: np.ndarray
    action: np.ndarray
    fps: Optional[float] = None
    task: Optional[str] = None
    task_index: Optional[int] = None
    source: str = "unknown"

    def __post_init__(self) -> None:
        raw_episode_index = float(self.episode_index)
        if not np.isfinite(raw_episode_index) or not raw_episode_index.is_integer():
            raise ValueError("episode_index must be a finite integer")
        self.episode_index = int(raw_episode_index)
        self.timestamp = np.asarray(self.timestamp, dtype=np.float64)
        raw_frame_index = np.asarray(self.frame_index)
        try:
            numeric_frame_index = raw_frame_index.astype(np.float64)
        except (TypeError, ValueError) as error:
            raise ValueError("frame_index must contain integers") from error
        if (not np.isfinite(numeric_frame_index).all()
                or not np.equal(numeric_frame_index, np.floor(numeric_frame_index)).all()):
            raise ValueError("frame_index must contain finite integers")
        self.frame_index = numeric_frame_index.astype(np.int64)
        self.state = np.asarray(self.state, dtype=np.float64)
        self.action = np.asarray(self.action, dtype=np.float64)
        self.source = str(self.source or "unknown")
        if self.task is not None:
            task = str(self.task).strip()
            self.task = task or None
        if self.task_index is not None:
            self.task_index = int(self.task_index)
        if self.fps is not None:
            self.fps = float(self.fps)
            if not np.isfinite(self.fps) or self.fps <= 0:
                raise ValueError("fps must be a positive finite number")

        if self.timestamp.ndim != 1 or self.frame_index.ndim != 1:
            raise ValueError("timestamp and frame_index must be one-dimensional")
        if self.state.ndim != 2 or self.action.ndim != 2:
            raise ValueError("state and action must be two-dimensional")
        lengths = {
            len(self.timestamp), len(self.frame_index),
            self.state.shape[0], self.action.shape[0],
        }
        if len(lengths) != 1:
            raise ValueError("timestamp, frame_index, state, and action lengths must match")
        if self.state.shape[1] == 0 or self.action.shape[1] == 0:
            raise ValueError("state and action must each contain at least one channel")

    @property
    def n_frames(self) -> int:
        return len(self.frame_index)

    @property
    def channels(self) -> np.ndarray:
        """State and action stacked as ``(n_frames, n_channels)``."""
        return np.hstack([self.state, self.action])

    def channel_names(self) -> List[str]:
        return ([f"state_{i}" for i in range(self.state.shape[1])] +
                [f"action_{i}" for i in range(self.action.shape[1])])


def _stack(col: pd.Series, name: str) -> np.ndarray:
    values = [np.asarray(value, dtype=np.float64) for value in col.to_numpy()]
    if not values:
        raise ValueError(f"{name} contains no rows")
    if any(value.ndim != 1 for value in values):
        raise ValueError(f"{name} entries must be one-dimensional vectors")
    widths = {len(value) for value in values}
    if len(widths) != 1:
        raise ValueError(f"{name} vector widths are inconsistent")
    return np.vstack(values)


def _task_value(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple, np.ndarray)):
        value = value[0] if len(value) else None
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def load_parquet(
    path: Path,
    fps: Optional[float] = None,
    *,
    tasks_by_episode: Optional[Mapping[int, str]] = None,
    source: Optional[str] = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> List[Episode]:
    """Load one bounded parquet file containing one or more episodes.

    The original row order is preserved so duplicate/backward frame indices remain
    visible to integrity checks instead of being hidden by sorting.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"frame parquet not found: {path}")
    if path.stat().st_size > max_file_bytes:
        raise ValueError(
            f"parquet is {path.stat().st_size / 1e6:.1f} MB; "
            f"limit is {max_file_bytes / 1e6:.1f} MB"
        )

    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows > max_rows:
        raise ValueError(
            f"parquet has {parquet.metadata.num_rows:,} rows; limit is {max_rows:,}"
        )
    columns = set(parquet.schema_arrow.names)
    missing = sorted(REQUIRED_FRAME_COLUMNS - columns)
    if missing:
        raise ValueError(f"parquet is missing required columns: {missing}")

    optional = [name for name in ("task_index", "task") if name in columns]
    df = pd.read_parquet(path, columns=sorted(REQUIRED_FRAME_COLUMNS) + optional)
    if df.empty:
        raise ValueError("parquet contains no frames")
    for column in ("episode_index", "frame_index"):
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.isna().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise ValueError(f"{column} contains non-finite or non-numeric values")
        if not np.equal(numeric.to_numpy(dtype=float), np.floor(numeric)).all():
            raise ValueError(f"{column} must contain integers")
        df[column] = numeric.astype(np.int64)
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")

    episode_source = source or path.stem
    episodes: List[Episode] = []
    for ep_idx, group in df.groupby("episode_index", sort=True, dropna=False):
        task_index = None
        if "task_index" in group:
            task_values = group["task_index"].dropna().unique()
            if len(task_values) > 1:
                raise ValueError(f"episode {ep_idx} contains multiple task_index values")
            if len(task_values) == 1:
                task_index = int(task_values[0])

        task = None
        if tasks_by_episode is not None:
            task = _task_value(tasks_by_episode.get(int(ep_idx)))
        elif "task" in group:
            task_values = [_task_value(value) for value in group["task"].tolist()]
            task_values = {value for value in task_values if value}
            if len(task_values) > 1:
                raise ValueError(f"episode {ep_idx} contains multiple task descriptions")
            task = next(iter(task_values), None)

        episodes.append(Episode(
            episode_index=int(ep_idx),
            timestamp=group["timestamp"].to_numpy(dtype=np.float64),
            frame_index=group["frame_index"].to_numpy(dtype=np.int64),
            state=_stack(group["observation.state"], "observation.state"),
            action=_stack(group["action"], "action"),
            fps=fps,
            task=task,
            task_index=task_index,
            source=episode_source,
        ))
    return episodes


def load_episode_file(path: Path, fps: Optional[float] = None, **kwargs) -> Episode:
    """Load a parquet that must contain exactly one episode."""
    episodes = load_parquet(path, fps, **kwargs)
    if len(episodes) != 1:
        raise ValueError(f"expected one episode in {path}, got {len(episodes)}")
    return episodes[0]
