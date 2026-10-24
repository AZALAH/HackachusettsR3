"""Tests for the transport-agnostic collector adapter."""

from __future__ import annotations

import numpy as np
import pytest

from datamon.collector import (
    BackpressurePolicy,
    CollectorAdapter,
    Frame,
)
from datamon.frames import Episode
from datamon.gate import Decision, GateConfig, IngestGate


def make_episode(idx=0, n=60, fps=15.0, seed=0, noise=0.05, task="move block"):
    rng = np.random.default_rng(seed)
    return Episode(
        idx,
        np.arange(n) / fps,
        np.arange(n),
        np.cumsum(rng.normal(0, noise, (n, 7)), axis=0),
        np.cumsum(rng.normal(0, noise, (n, 7)), axis=0),
        fps=fps,
        task=task,
        task_index=1,
        source="collector-rig",
    )


@pytest.fixture
def gate(tmp_path):
    instance = IngestGate(tmp_path / "ingest", GateConfig())
    return instance.calibrate([make_episode(i, seed=i) for i in range(20)])


def _frames_from(episode: Episode):
    for position in range(episode.n_frames):
        yield Frame(
            episode_index=episode.episode_index,
            frame_index=int(episode.frame_index[position]),
            timestamp=float(episode.timestamp[position]),
            state=episode.state[position],
            action=episode.action[position],
            task=episode.task,
            task_index=episode.task_index,
            source=episode.source,
        )


def test_single_episode_gated_on_disconnect(gate):
    adapter = CollectorAdapter(gate, fps=15.0)
    episode = make_episode(1000, seed=11)
    for frame in _frames_from(episode):
        assert adapter.submit(frame)
    result = adapter.disconnect()
    assert result is not None
    assert result.decision in (Decision.ACCEPT, Decision.REVIEW, Decision.REJECT)
    assert result.stored_path is not None
    assert adapter.stats.episodes_completed == 1
    assert adapter.stats.frames_ingested == episode.n_frames


def test_new_episode_id_closes_the_previous_one(gate):
    adapter = CollectorAdapter(gate, fps=15.0)
    first = make_episode(1001, seed=12)
    second = make_episode(1002, seed=13)
    for frame in _frames_from(first):
        adapter.submit(frame)
    for frame in _frames_from(second):
        adapter.submit(frame)
    completed = adapter.drain()
    assert len(completed) == 1  # first closed when second's id arrived
    tail = adapter.disconnect()
    assert tail is not None
    assert adapter.stats.episodes_completed == 2


def test_short_partial_is_discarded_on_disconnect(gate):
    adapter = CollectorAdapter(gate, fps=15.0, min_frames_on_disconnect=5)
    episode = make_episode(1003, n=3, seed=14)
    for frame in _frames_from(episode):
        adapter.submit(frame)
    result = adapter.disconnect()
    assert result is None
    assert adapter.stats.partials_discarded == 1
    assert adapter.stats.episodes_completed == 0


def test_long_partial_is_salvaged_on_disconnect(gate):
    adapter = CollectorAdapter(gate, fps=15.0, min_frames_on_disconnect=5)
    episode = make_episode(1004, n=40, seed=15)
    for frame in _frames_from(episode):
        adapter.submit(frame)
    result = adapter.disconnect()
    assert result is not None
    assert adapter.stats.partials_salvaged == 1


def test_drop_oldest_backpressure_counts_drops(gate):
    adapter = CollectorAdapter(
        gate, fps=15.0, max_queue=10,
        backpressure=BackpressurePolicy.DROP_OLDEST,
    )
    episode = make_episode(1005, n=25, seed=16)
    for frame in _frames_from(episode):
        assert adapter.submit(frame) is True
    assert adapter.stats.frames_dropped_backpressure == 15
    assert len(adapter._queue) == 10


def test_block_producer_backpressure_rejects_when_full(gate):
    adapter = CollectorAdapter(
        gate, fps=15.0, max_queue=5,
        backpressure=BackpressurePolicy.BLOCK_PRODUCER,
    )
    episode = make_episode(1006, n=8, seed=17)
    accepted = [adapter.submit(frame) for frame in _frames_from(episode)]
    assert accepted[:5] == [True] * 5
    assert accepted[5:] == [False] * 3
    assert adapter.stats.frames_dropped_backpressure == 0


def test_abort_discards_open_episode(gate):
    adapter = CollectorAdapter(gate, fps=15.0)
    episode = make_episode(1007, n=40, seed=18)
    for frame in _frames_from(episode):
        adapter.submit(frame)
    adapter.drain()
    adapter.abort()
    assert adapter.stats.episodes_completed == 0
    assert adapter.stats.partials_discarded == 1
    # The gate must not have stored anything for this aborted episode.
    assert sum(gate.stats().values()) == 0


def test_on_episode_callback_fires(gate):
    seen = []
    adapter = CollectorAdapter(gate, fps=15.0, on_episode=seen.append)
    for frame in _frames_from(make_episode(1008, seed=19)):
        adapter.submit(frame)
    adapter.disconnect()
    assert len(seen) == 1


def test_invalid_config_is_rejected(gate):
    with pytest.raises(ValueError, match="max_queue"):
        CollectorAdapter(gate, fps=15.0, max_queue=0)
    with pytest.raises(ValueError, match="min_frames_on_disconnect"):
        CollectorAdapter(gate, fps=15.0, min_frames_on_disconnect=0)
