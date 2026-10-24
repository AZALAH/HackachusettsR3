"""Tests for frame-level stream quality checks."""

import numpy as np

from datamon.frame_quality import (
    Severity,
    analyze_frames,
    check_dropped_frames,
    check_out_of_range,
    check_sensor_noise,
    check_stuck_channels,
    check_timing_drift,
)
from datamon.frames import Episode


def make_episode(n=40, state_dim=6, action_dim=4, fps=5.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fps
    fi = np.arange(n)
    # smooth, continuous trajectories
    state = np.cumsum(rng.normal(0, 0.05, (n, state_dim)), axis=0)
    action = np.cumsum(rng.normal(0, 0.05, (n, action_dim)), axis=0)
    return Episode(0, t, fi, state, action, fps=fps)


def test_clean_episode_has_no_errors():
    ep = make_episode()
    rep = analyze_frames(ep)
    assert not rep.has_error()


def test_dropped_frames_detected():
    ep = make_episode(n=40)
    keep = np.ones(40, dtype=bool)
    keep[20:23] = False
    ep = Episode(0, ep.timestamp[keep], ep.frame_index[keep],
                 ep.state[keep], ep.action[keep], fps=5.0)
    flags = check_dropped_frames(ep)
    assert any(f.check == "dropped_frames" and f.severity == Severity.ERROR
               for f in flags)


def test_timing_drift_detected():
    ep = make_episode(n=40)
    ep.timestamp = np.cumsum(np.linspace(0.2, 0.4, 40))
    flags = check_timing_drift(ep, nominal_dt=0.2)
    assert any(f.check == "timing_drift" for f in flags)


def test_stuck_continuous_channel_detected():
    ep = make_episode(n=40)
    ep.state[10:, 0] = ep.state[10, 0]  # freeze a continuous channel 75% of ep
    flags = check_stuck_channels(ep)
    assert any(f.check == "stuck_channel" and f.channel == "state_0"
               and f.severity == Severity.WARN for f in flags)


def test_discrete_gripper_not_flagged_stuck():
    ep = make_episode(n=40)
    # make action_0 a binary gripper that holds then flips
    ep.action[:, 0] = 0.0
    ep.action[25:, 0] = 1.0
    flags = check_stuck_channels(ep)
    assert not any(f.channel == "action_0" and f.severity == Severity.WARN
                   for f in flags)


def test_nan_detected_without_warning():
    ep = make_episode(n=40)
    ep.state[5, 2] = np.nan
    flags = check_out_of_range(ep)
    assert any(f.check == "out_of_range" and f.channel == "state_2" for f in flags)


def test_out_of_range_with_config():
    ep = make_episode(n=40)
    ep.state[:, 1] += 100.0
    flags = check_out_of_range(ep, ranges={"state_1": (-1.0, 1.0)})
    assert any(f.check == "out_of_range" for f in flags)


def test_noisy_channel_detected():
    ep = make_episode(n=60)
    rng = np.random.default_rng(1)
    ep.state[:, 3] += rng.normal(0, 5.0, 60)  # one very noisy state channel
    flags = check_sensor_noise(ep)
    assert any(f.check == "sensor_noise" and f.channel == "state_3" for f in flags)


def test_duplicate_and_backward_indices_are_integrity_errors():
    episode = make_episode(n=8)
    episode.frame_index = np.array([0, 1, 2, 2, 3, 6, 5, 6])
    flags = check_dropped_frames(episode)
    reasons = " ".join(flag.reason for flag in flags)
    assert "duplicate" in reasons
    assert "missing" in reasons
    assert "backward" in reasons


def test_nonzero_initial_frame_is_detected():
    episode = make_episode(n=8)
    episode.frame_index += 10
    flags = check_dropped_frames(episode)
    assert any("starts at" in flag.reason for flag in flags)


def test_consistently_wrong_cadence_is_detected():
    episode = make_episode(n=30, fps=5.0)
    episode.timestamp = np.arange(30) * 0.3  # stable, but 50% too slow
    flags = check_timing_drift(episode, nominal_dt=0.2, jitter_tol=0.25)
    assert any("median interval" in flag.reason for flag in flags)


def test_nonfinite_timestamp_is_detected():
    episode = make_episode(n=20)
    episode.timestamp[4] = np.nan
    flags = check_out_of_range(episode)
    assert any(flag.channel == "timestamp" for flag in flags)


def test_whole_episode_flatline_is_actionable():
    episode = make_episode(n=20)
    episode.state[:, 0] = 0.0
    flags = check_stuck_channels(episode)
    assert any(
        flag.channel == "state_0" and flag.severity == Severity.WARN
        for flag in flags
    )
