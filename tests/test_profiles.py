"""Tests for named robot profiles and their persistent store."""

from __future__ import annotations

import pytest

from datamon.frame_quality import DetectorConfig
from datamon.profiles import ProfileStore, RobotProfile


def _profile(name="franka_panda"):
    return RobotProfile(
        name=name,
        fps=20.0,
        jitter_tolerance=0.3,
        cadence_tolerance=0.2,
        channel_roles={"state_0": "shoulder_pan", "state_6": "gripper"},
        ranges={"state_0": [-2.9, 2.9], "action_0": [-1.0, 1.0]},
        allowed_static_channels=["state_6", "action_6"],
        task_family="tabletop_manipulation",
    )


def test_profile_projects_to_detector_config():
    config = _profile().to_detector_config()
    assert isinstance(config, DetectorConfig)
    assert config.jitter_tolerance == 0.3
    assert config.cadence_tolerance == 0.2
    assert config.ranges["state_0"] == (-2.9, 2.9)
    assert "state_6" in config.allowed_static_channels


def test_profile_round_trips_through_dict():
    original = _profile()
    restored = RobotProfile.from_dict(original.to_dict())
    assert restored == original


def test_profile_rejects_bad_name():
    with pytest.raises(ValueError, match="profile name"):
        RobotProfile(name="")
    with pytest.raises(ValueError, match="profile name"):
        RobotProfile(name="bad/name")


def test_profile_rejects_bad_fps_and_tolerance():
    with pytest.raises(ValueError, match="fps"):
        RobotProfile(name="rig", fps=0)
    with pytest.raises(ValueError, match="jitter_tolerance"):
        RobotProfile(name="rig", jitter_tolerance=2.0)


def test_profile_rejects_inverted_range():
    with pytest.raises(ValueError, match="invalid range"):
        RobotProfile(name="rig", ranges={"state_0": [1.0, -1.0]})


def test_store_save_and_get(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(_profile())
    loaded = store.get("franka_panda")
    assert loaded.task_family == "tabletop_manipulation"
    assert loaded.channel_roles["state_6"] == "gripper"


def test_store_overwrites_same_name(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(_profile())
    updated = _profile()
    updated.fps = 30.0
    store.save(updated)
    assert store.get("franka_panda").fps == 30.0
    assert store.names() == ["franka_panda"]


def test_store_lists_and_deletes(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(_profile("rig_a"))
    store.save(_profile("rig_b"))
    assert store.names() == ["rig_a", "rig_b"]
    assert store.delete("rig_a") is True
    assert store.delete("rig_a") is False
    assert store.names() == ["rig_b"]


def test_store_get_unknown_raises(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    with pytest.raises(KeyError):
        store.get("missing")


def test_store_tolerates_corrupt_file(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text("{ not valid json", encoding="utf-8")
    store = ProfileStore(path)
    assert store.names() == []  # corrupt file reads as empty, not a crash
    store.save(_profile())
    assert store.names() == ["franka_panda"]
