"""Tests for the guided tour step definitions and audio resolution."""

from __future__ import annotations

import datamon.tour as tour
from datamon.tour import TOUR_STEPS, audio_path_for


def test_steps_have_unique_ordered_ids():
    ids = [step.step_id for step in TOUR_STEPS]
    assert len(ids) == len(set(ids))  # unique
    assert ids == sorted(ids)         # already in numeric step order


def test_every_step_has_caption_and_target():
    for step in TOUR_STEPS:
        assert step.title.strip()
        assert step.caption.strip()
        assert step.target.strip()
        assert step.arrow.strip()


def test_audio_path_prefers_mp3_over_wav(tmp_path, monkeypatch):
    monkeypatch.setattr(tour, "AUDIO_DIR", tmp_path)
    (tmp_path / "step_01_welcome.wav").write_bytes(b"wav")
    (tmp_path / "step_01_welcome.mp3").write_bytes(b"mp3")
    assert audio_path_for("step_01_welcome").suffix == ".mp3"


def test_audio_path_falls_back_to_wav(tmp_path, monkeypatch):
    monkeypatch.setattr(tour, "AUDIO_DIR", tmp_path)
    (tmp_path / "alert_error.wav").write_bytes(b"wav")
    assert audio_path_for("alert_error").suffix == ".wav"


def test_audio_path_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(tour, "AUDIO_DIR", tmp_path)
    assert audio_path_for("nope") is None


def test_go_to_step_clamps_and_counts_visits():
    state = {}
    tour.go_to_step(state, 3)
    assert state["tour_active"] is True
    assert state["tour_index"] == 3
    assert state["tour_visit"] == 1
    # Back from the first step and past the last step both stay in range.
    tour.go_to_step(state, -1)
    assert state["tour_index"] == 0
    tour.go_to_step(state, len(TOUR_STEPS) + 5)
    assert state["tour_index"] == len(TOUR_STEPS) - 1
    # Each visit is distinct, so a revisited step's narration plays again.
    assert state["tour_visit"] == 3


def test_end_tour_deactivates():
    state = {"tour_active": True}
    tour.end_tour(state)
    assert state["tour_active"] is False
