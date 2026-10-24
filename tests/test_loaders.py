"""Schema and orchestration regression tests."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from datamon.frames import Episode, load_parquet
from datamon.lerobot import load_episodes, load_info, task_map
from datamon.monitor import Monitor


def frame_data(episode_indices=(0, 0, 0)) -> pd.DataFrame:
    rows = len(episode_indices)
    return pd.DataFrame({
        "observation.state": [np.array([i, i + 1.0]) for i in range(rows)],
        "action": [np.array([i * 0.1]) for i in range(rows)],
        "timestamp": np.arange(rows) / 5.0,
        "frame_index": np.arange(rows),
        "episode_index": list(episode_indices),
        "task_index": np.zeros(rows, dtype=int),
    })


def test_episode_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="lengths must match"):
        Episode(0, np.arange(2), np.arange(3), np.zeros((3, 2)), np.zeros((3, 1)))


def test_frame_loader_preserves_bad_order_for_detection(tmp_path):
    frame = frame_data()
    frame["frame_index"] = [0, 2, 1]
    path = tmp_path / "frames.parquet"
    frame.to_parquet(path)
    episode = load_parquet(path, fps=5.0)[0]
    assert episode.frame_index.tolist() == [0, 2, 1]


def test_frame_loader_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.parquet"
    pd.DataFrame({"episode_index": [0]}).to_parquet(path)
    with pytest.raises(ValueError, match="missing required columns"):
        load_parquet(path)


def test_frame_loader_applies_task_mapping(tmp_path):
    path = tmp_path / "frames.parquet"
    frame_data().to_parquet(path)
    episode = load_parquet(
        path, fps=5.0, tasks_by_episode={0: "pick cube"}, source="fixture",
    )[0]
    assert episode.task == "pick cube"
    assert episode.source == "fixture"


def test_load_v2_episode_jsonl(tmp_path):
    meta = tmp_path / "meta"
    meta.mkdir()
    (meta / "episodes.jsonl").write_text(
        json.dumps({"episode_index": 4, "tasks": ["open drawer"], "length": 20}) + "\n",
        encoding="utf-8",
    )
    episodes = load_episodes(tmp_path)
    assert task_map(episodes) == {4: "open drawer"}


def test_load_v3_episode_parquet(tmp_path):
    path = tmp_path / "meta" / "episodes" / "chunk-000"
    path.mkdir(parents=True)
    pd.DataFrame({
        "episode_index": [2], "tasks": [["close drawer"]], "length": [25],
    }).to_parquet(path / "file-000.parquet")
    episodes = load_episodes(tmp_path)
    assert episodes.iloc[0]["task"] == "close drawer"


def test_info_requires_valid_fps(tmp_path):
    meta = tmp_path / "meta"
    meta.mkdir()
    (meta / "info.json").write_text(json.dumps({
        "fps": 0, "total_episodes": 1, "total_frames": 1, "features": {},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid fps"):
        load_info(tmp_path)


def test_monitor_rejects_empty_and_duplicate_sets():
    with pytest.raises(ValueError, match="at least one"):
        Monitor([])
    episode = Episode(
        0, np.array([0.0]), np.array([0]), np.zeros((1, 1)), np.zeros((1, 1)),
        fps=5.0, task="test", source="fixture",
    )
    with pytest.raises(ValueError, match="unique"):
        Monitor([episode, episode])
