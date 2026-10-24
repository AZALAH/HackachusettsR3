"""Tests for task-conditioned anomaly baselines."""

from __future__ import annotations

import numpy as np

from datamon.frames import Episode
from datamon.gate import GateConfig, IngestGate
from datamon.scoring import (
    TaskConditionedAnomalyModel,
    episode_feature_vector,
    fit_task_conditioned_model,
)


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
        source="test-rig",
    )


def _two_task_corpus():
    # Two clearly different task families: short/slow vs long/fast.
    pick = [make_episode(i, n=30, seed=i, noise=0.02, task="pick cube")
            for i in range(12)]
    sweep = [make_episode(100 + i, n=90, seed=100 + i, noise=0.12, task="sweep table")
             for i in range(12)]
    return pick + sweep


def test_fits_a_model_per_populated_task():
    model = fit_task_conditioned_model(_two_task_corpus(), min_per_task=8)
    assert isinstance(model, TaskConditionedAnomalyModel)
    assert set(model.task_names) == {"pick cube", "sweep table"}
    assert model.fallback is not None


def test_thin_task_uses_global_fallback_only():
    corpus = _two_task_corpus()
    corpus += [make_episode(200, n=45, seed=200, task="rare task")]  # only 1
    model = fit_task_conditioned_model(corpus, min_per_task=8)
    assert "rare task" not in model.task_names
    # A rare-task vector still scores via the fallback rather than returning None.
    vector = episode_feature_vector(make_episode(201, n=45, seed=201, task="rare task"))
    assert model.score(vector, "rare task") is not None


def test_task_key_is_case_insensitive():
    model = fit_task_conditioned_model(_two_task_corpus(), min_per_task=8)
    vector = episode_feature_vector(make_episode(5, n=30, seed=5, task="PICK CUBE"))
    assert model.score(vector, "PICK CUBE") is not None


def test_score_is_bounded_zero_to_one():
    model = fit_task_conditioned_model(_two_task_corpus(), min_per_task=8)
    vector = episode_feature_vector(make_episode(9, n=30, seed=9, task="pick cube"))
    value = model.score(vector, "pick cube")
    assert 0.0 <= value <= 1.0


def test_gate_calibrate_per_task_uses_conditioned_model(tmp_path):
    gate = IngestGate(tmp_path / "ingest", GateConfig())
    gate.calibrate_per_task(_two_task_corpus(), min_per_task=8)
    assert isinstance(gate.anomaly_model, TaskConditionedAnomalyModel)
    result = gate.evaluate(make_episode(300, n=30, seed=7, task="pick cube"))
    assert result.score.anomaly_score is not None


def test_empty_corpus_yields_no_models():
    model = fit_task_conditioned_model([], min_per_task=8)
    assert model.task_names == []
    assert model.fallback is None
    assert model.score(np.zeros(7), "anything") is None
