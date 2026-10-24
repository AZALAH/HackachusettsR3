"""Tests for Phase C: episode quality scoring + anomaly model."""

import numpy as np

from datamon.episode_quality import Flag as EpFlag
from datamon.episode_quality import Severity as EpSev
from datamon.frame_quality import analyze_frames, check_saturation, check_stuck_channels
from datamon.frames import Episode
from datamon.scoring import (
    episode_feature_vector,
    fit_anomaly_model,
    rule_score_from_flags,
    score_episode,
)


def make_episode(n=60, state_dim=7, action_dim=7, fps=15.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fps
    fi = np.arange(n)
    state = np.cumsum(rng.normal(0, 0.05, (n, state_dim)), axis=0)
    action = np.cumsum(rng.normal(0, 0.05, (n, action_dim)), axis=0)
    return Episode(0, t, fi, state, action, fps=fps)


def test_clean_episode_scores_high():
    ep = make_episode()
    s = score_episode(ep.episode_index, frame_report=analyze_frames(ep))
    assert s.score >= 80
    assert s.grade == "good"


def test_errors_tank_the_score():
    flags = [EpFlag(0, "missing_label", EpSev.ERROR, "no label"),
             EpFlag(0, "degenerate_length", EpSev.ERROR, "2 frames")]
    score, reasons = rule_score_from_flags(flags)
    assert score <= 55
    assert len(reasons) == 2


def test_info_flags_do_not_penalize():
    flags = [EpFlag(0, "duplicate_label", EpSev.INFO, "common task")]
    score, reasons = rule_score_from_flags(flags)
    assert score == 100.0
    assert reasons == []


def test_grade_thresholds():
    assert score_episode(0, episode_flags=[]).grade == "good"
    score = score_episode(
        0,
        episode_flags=[EpFlag(0, f"check_{i}", EpSev.WARN, "x") for i in range(4)],
    )
    assert score.grade in ("review", "reject")


def test_resting_gripper_not_flagged_stuck_or_saturated():
    ep = make_episode(n=100)
    # continuous gripper on state_6: moves, then rests fully open (min) a long time
    ep.state[:, 6] = 0.0
    ep.state[20:30, 6] = np.linspace(0, 0.8, 10)  # a grasp
    ep.state[30:40, 6] = 0.8
    ep.state[40:50, 6] = np.linspace(0.8, 0.0, 10)
    # frames 50-100 rest at 0.0 (open)
    stuck = check_stuck_channels(ep)
    sat = check_saturation(ep)
    assert not any(f.channel == "state_6" and f.severity.value == "warn" for f in stuck)
    assert not any(f.channel == "state_6" for f in sat)


def test_midrange_freeze_is_flagged():
    ep = make_episode(n=80)
    # state_0 freezes at a mid-range active value for most of the episode
    ep.state[20:, 0] = ep.state[20, 0]
    # ensure the held value is interior (shift so it's not an extreme)
    ep.state[:20, 0] = np.linspace(-1, 1, 20)
    ep.state[20:, 0] = 0.3  # interior value
    stuck = check_stuck_channels(ep)
    assert any(f.channel == "state_0" and f.severity.value == "warn" for f in stuck)


def test_anomaly_model_flags_outlier():
    eps = [make_episode(n=60, seed=i) for i in range(20)]
    # one wildly different episode: huge motion
    odd = make_episode(n=60, seed=99)
    odd.state *= 50.0
    model = fit_anomaly_model(eps + [odd])
    assert model is not None
    normal = np.median([model.score(episode_feature_vector(e)) for e in eps])
    outlier = model.score(episode_feature_vector(odd))
    assert outlier > normal


def test_repeated_observations_of_one_check_are_not_double_counted():
    flags = [
        EpFlag(0, "dropped_frames", EpSev.ERROR, "index gap"),
        EpFlag(0, "dropped_frames", EpSev.ERROR, "timestamp gap"),
    ]
    score, reasons = rule_score_from_flags(flags)
    assert score == 75.0
    assert len(reasons) == 2


def test_unavailable_anomaly_is_explicit():
    score = score_episode(0)
    assert score.anomaly_score is None
    assert score.as_dict()["anomaly_score"] is None
