"""Tests for content-addressed gating and bounded live ingestion."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datamon.frames import Episode, load_episode_file
from datamon.gate import Decision, GateConfig, IngestGate, OperatorAction
from datamon.stream import StreamIngestor


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


@pytest.fixture
def gate(tmp_path):
    instance = IngestGate(tmp_path / "ingest", GateConfig())
    return instance.calibrate([make_episode(i, seed=i) for i in range(20)])


def test_clean_episode_is_not_rejected(gate):
    result = gate.admit(make_episode(100, seed=100))
    assert result.decision in (Decision.ACCEPT, Decision.REVIEW)
    assert result.stored_path and result.ingest_id
    assert Path(result.stored_path).is_file()


def test_missing_task_is_hard_rejected(gate):
    result = gate.admit(make_episode(104, task=None))
    assert result.decision == Decision.REJECT
    assert any("missing_label" in reason for reason in result.reasons)


def test_dropped_frames_are_hard_rejected(gate):
    episode = make_episode(101)
    keep = np.ones(episode.n_frames, bool)
    keep[20:25] = False
    episode = Episode(
        101, episode.timestamp[keep], episode.frame_index[keep],
        episode.state[keep], episode.action[keep], fps=15.0,
        task=episode.task, source=episode.source,
    )
    result = gate.admit(episode)
    assert result.decision == Decision.REJECT
    assert any("dropped_frames" in reason for reason in result.reasons)


def test_nan_is_hard_rejected(gate):
    episode = make_episode(102)
    episode.state[5, 0] = np.nan
    assert gate.admit(episode).decision == Decision.REJECT


def test_too_short_is_rejected(gate):
    assert gate.admit(make_episode(103, n=3)).decision == Decision.REJECT


def test_saved_parquet_contains_only_exact_evaluated_episode(gate):
    episode = make_episode(210, n=17, task="pick the cube")
    result = gate.admit(episode)
    stored = load_episode_file(Path(result.stored_path), fps=15.0)
    assert stored.episode_index == 210
    assert stored.n_frames == 17
    assert stored.task == "pick the cube"
    np.testing.assert_array_equal(stored.state, episode.state)
    np.testing.assert_array_equal(stored.action, episode.action)


def test_stats_count_latest_content_once(gate):
    episode = make_episode(220)
    first = gate.admit(episode)
    second = gate.admit(episode)
    assert first.ingest_id == second.ingest_id
    assert sum(gate.stats().values()) == 1


def test_changed_policy_moves_same_content_between_routes(tmp_path):
    root = tmp_path / "ingest"
    episode = make_episode(230)
    episode.state[:10, 0] = np.linspace(-1.0, 1.0, 10)
    episode.state[10:, 0] = 0.25  # mid-range freeze keeps score below 100
    permissive = IngestGate(
        root, GateConfig(accept_at=0, reject_below=0, require_task=True)
    )
    first = permissive.admit(episode)
    assert first.decision == Decision.ACCEPT
    assert Path(first.stored_path).is_file()

    strict = IngestGate(
        root, GateConfig(accept_at=100, reject_below=100, require_task=True)
    )
    second = strict.admit(episode)
    assert second.decision == Decision.REJECT
    assert second.ingest_id == first.ingest_id
    assert Path(second.stored_path).is_file()
    assert not Path(first.stored_path).exists()
    assert sum(strict.stats().values()) == 1


def test_manifest_tolerates_a_truncated_line(gate):
    result = gate.admit(make_episode(240))
    with gate.manifest.open("a", encoding="utf-8") as handle:
        handle.write("{truncated\n")
    assert sum(gate.stats().values()) == 1
    assert result.ingest_id in gate._latest_records()


def test_wasted_frames_metric_uses_latest_rejections(gate):
    episode = make_episode(300, n=40)
    episode.state[5, 0] = np.inf
    gate.admit(episode)
    assert gate.wasted_frames_prevented() == 40


def test_evaluate_does_not_write(gate):
    before = list(gate.root.rglob("*.parquet"))
    gate.evaluate(make_episode(400, seed=5))
    assert list(gate.root.rglob("*.parquet")) == before


def test_stream_per_frame_feedback(gate):
    seen = []
    ingestor = StreamIngestor(gate, fps=15.0, on_frame=seen.append)
    episode = make_episode(500)
    ingestor.replay_episode(episode)
    assert len(seen) == episode.n_frames
    assert all(feedback.ok for feedback in seen)


def test_stream_detects_dropped_frame_live(gate):
    warnings = []
    ingestor = StreamIngestor(
        gate, fps=15.0,
        on_frame=lambda feedback: warnings.extend(feedback.warnings),
    )
    for frame_index in [0, 1, 2, 7, 8]:
        ingestor.push_frame(
            600, frame_index, frame_index / 15.0,
            np.zeros(7), np.zeros(7), task="move block",
        )
    assert any("dropped" in warning for warning in warnings)


def test_stream_rejects_cross_episode_mix(gate):
    ingestor = StreamIngestor(gate, fps=15.0)
    ingestor.push_frame(1, 0, 0.0, np.zeros(7), np.zeros(7), task="move block")
    with pytest.raises(ValueError, match="still open"):
        ingestor.push_frame(2, 1, 1 / 15.0, np.zeros(7), np.zeros(7))


def test_stream_resets_even_when_callback_fails(gate):
    ingestor = StreamIngestor(
        gate, fps=15.0,
        on_episode=lambda _: (_ for _ in ()).throw(RuntimeError("callback failed")),
    )
    episode = make_episode(700)
    with pytest.raises(RuntimeError, match="callback failed"):
        ingestor.replay_episode(episode)
    assert ingestor.end_episode() is None


def test_invalid_threshold_order_is_rejected():
    with pytest.raises(ValueError, match="thresholds"):
        GateConfig(accept_at=50, reject_below=60)


# --- Operator review loop ---------------------------------------------------


def _review_gate(tmp_path):
    """A gate whose only item lands in review (score forces the middle band)."""
    root = tmp_path / "ingest"
    gate = IngestGate(
        root, GateConfig(accept_at=100, reject_below=0, require_task=True)
    )
    episode = make_episode(800, seed=3)
    # A mid-range freeze costs quality points without an integrity hard-reject,
    # so the score lands strictly below accept_at (100) and above reject_below (0).
    episode.state[:10, 0] = np.linspace(-1.0, 1.0, 10)
    episode.state[10:, 0] = 0.25
    result = gate.admit(episode)
    assert result.decision == Decision.REVIEW
    return gate, result


def test_review_queue_lists_pending_items(tmp_path):
    gate, result = _review_gate(tmp_path)
    queue = gate.review_queue()
    assert len(queue) == 1
    assert queue[0]["ingest_id"] == result.ingest_id


def test_promote_moves_review_to_clean(tmp_path):
    gate, result = _review_gate(tmp_path)
    outcome = gate.operator_decision(result.ingest_id, OperatorAction.PROMOTE)
    assert outcome.decision == Decision.ACCEPT
    assert outcome.ingest_id == result.ingest_id
    assert Path(outcome.stored_path).is_file()
    assert "clean" in Path(outcome.stored_path).parts
    assert not Path(result.stored_path).exists()
    assert gate.stats()["accept"] == 1
    assert gate.review_queue() == []


def test_reject_moves_review_to_quarantine(tmp_path):
    gate, result = _review_gate(tmp_path)
    outcome = gate.operator_decision(
        result.ingest_id, OperatorAction.REJECT, note="jerky trajectory"
    )
    assert outcome.decision == Decision.REJECT
    assert "quarantine" in Path(outcome.stored_path).parts
    assert gate.stats()["reject"] == 1


def test_recollect_keeps_item_in_review_with_audit(tmp_path):
    gate, result = _review_gate(tmp_path)
    outcome = gate.operator_decision(
        result.ingest_id, OperatorAction.RECOLLECT, note="recapture with fresh rig"
    )
    assert outcome.decision == Decision.REVIEW
    assert gate.review_queue()[0]["ingest_id"] == result.ingest_id
    history = gate.history(result.ingest_id)
    assert history[-1]["action"] == "operator_recollect"
    assert history[-1]["note"] == "recapture with fresh rig"


def test_history_preserves_every_event(tmp_path):
    gate, result = _review_gate(tmp_path)
    gate.operator_decision(result.ingest_id, OperatorAction.RECOLLECT)
    gate.operator_decision(result.ingest_id, OperatorAction.PROMOTE)
    history = gate.history(result.ingest_id)
    assert [event["action"] for event in history] == [
        "automated", "operator_recollect", "operator_promote",
    ]
    assert sum(gate.stats().values()) == 1


def test_operator_decision_rejects_unknown_id(tmp_path):
    gate, _ = _review_gate(tmp_path)
    with pytest.raises(KeyError):
        gate.operator_decision("deadbeef", OperatorAction.PROMOTE)


def test_cannot_act_on_item_not_in_review(tmp_path):
    gate, result = _review_gate(tmp_path)
    gate.operator_decision(result.ingest_id, OperatorAction.PROMOTE)
    with pytest.raises(ValueError, match="not in review"):
        gate.operator_decision(result.ingest_id, OperatorAction.REJECT)


def test_automated_action_is_not_a_valid_operator_decision(tmp_path):
    gate, result = _review_gate(tmp_path)
    with pytest.raises(ValueError, match="human review action"):
        gate.operator_decision(result.ingest_id, OperatorAction.AUTOMATED)
