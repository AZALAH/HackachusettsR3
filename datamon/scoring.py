"""Transparent rule scoring plus calibrated trajectory anomaly scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from datamon.frame_quality import FrameReport
from datamon.frames import Episode

SEVERITY_PENALTY = {"error": 25.0, "warn": 8.0, "info": 0.0}


@dataclass
class EpisodeScore:
    episode_index: int
    score: float
    rule_score: float
    anomaly_score: Optional[float]
    grade: str
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "episode_index": self.episode_index,
            "score": round(self.score, 1),
            "rule_score": round(self.rule_score, 1),
            "anomaly_score": (
                round(self.anomaly_score, 3) if self.anomaly_score is not None else None
            ),
            "grade": self.grade,
            "reasons": self.reasons,
        }


def grade_score(score: float, accept_at: float = 80.0,
                reject_below: float = 55.0) -> str:
    if not 0 <= reject_below <= accept_at <= 100:
        raise ValueError("thresholds must satisfy 0 <= reject_below <= accept_at <= 100")
    if score >= accept_at:
        return "good"
    if score < reject_below:
        return "reject"
    return "review"


def rule_score_from_flags(flags) -> tuple[float, List[str]]:
    """Deduct once per check using that check's most severe flag.

    Multiple observations of one physical problem (for example an index gap and
    its matching timestamp gap) remain visible in reasons without double-counting
    the quality penalty.
    """
    penalty_by_check: Dict[str, float] = {}
    reasons: List[str] = []
    for flag in flags:
        severity = (flag.severity.value if hasattr(flag.severity, "value")
                    else str(flag.severity))
        penalty_by_check[flag.check] = max(
            penalty_by_check.get(flag.check, 0.0),
            SEVERITY_PENALTY.get(severity, 0.0),
        )
        if severity in ("warn", "error"):
            reasons.append(f"{flag.check}: {flag.reason}")
    return max(0.0, 100.0 - sum(penalty_by_check.values())), reasons


def episode_feature_vector(ep: Episode) -> np.ndarray:
    """Summarize duration, motion, smoothness, and commanded effort."""
    state = np.nan_to_num(ep.state, nan=0.0, posinf=0.0, neginf=0.0)
    action = np.nan_to_num(ep.action, nan=0.0, posinf=0.0, neginf=0.0)
    dstate = np.diff(state, axis=0) if ep.n_frames > 1 else np.zeros_like(state)
    daction = np.diff(action, axis=0) if ep.n_frames > 1 else np.zeros_like(action)
    return np.array([
        float(ep.n_frames),
        float(np.mean(np.abs(dstate))),
        float(np.std(dstate)),
        float(np.mean(np.abs(action))),
        float(np.mean(np.abs(daction))),
        float(np.max(np.abs(dstate)) if dstate.size else 0.0),
        float(np.ptp(state)),
    ], dtype=np.float64)


@dataclass
class AnomalyModel:
    estimator: object
    scaler_mean: np.ndarray
    scaler_std: np.ndarray
    calibration_scores: np.ndarray

    def score(self, vector: np.ndarray) -> float:
        """Return a calibrated 0-1 upper-tail anomaly score.

        The lower half of reference observations maps to zero; increasingly rare
        upper-tail observations approach one. This is a rank score, not a model
        probability.
        """
        z = (vector - self.scaler_mean) / self.scaler_std
        raw = -float(self.estimator.score_samples(z.reshape(1, -1))[0])
        percentile = np.searchsorted(
            self.calibration_scores, raw, side="right"
        ) / len(self.calibration_scores)
        return float(np.clip((percentile - 0.5) / 0.5, 0.0, 1.0))


def fit_anomaly_model(episodes: List[Episode], seed: int = 42) -> Optional[AnomalyModel]:
    """Fit and empirically calibrate an IsolationForest on reference episodes."""
    if len(episodes) < 8:
        return None
    from sklearn.ensemble import IsolationForest

    vectors = np.vstack([episode_feature_vector(episode) for episode in episodes])
    mean = vectors.mean(axis=0)
    std = vectors.std(axis=0)
    std[std < 1e-9] = 1.0
    scaled = (vectors - mean) / std
    estimator = IsolationForest(random_state=seed, contamination="auto")
    estimator.fit(scaled)
    calibration = np.sort(-estimator.score_samples(scaled))
    return AnomalyModel(estimator, mean, std, calibration)


def score_episode(
    episode_index: int,
    episode_flags=None,
    frame_report: Optional[FrameReport] = None,
    anomaly: Optional[float] = None,
    anomaly_weight: float = 50.0,
    accept_at: float = 80.0,
    reject_below: float = 55.0,
) -> EpisodeScore:
    """Blend explainable flags and a calibrated anomaly score into 0-100."""
    all_flags = list(episode_flags or [])
    if frame_report is not None:
        all_flags.extend(frame_report.flags)
    rule_score, reasons = rule_score_from_flags(all_flags)

    anomaly_penalty = 0.0 if anomaly is None else anomaly * anomaly_weight
    final = max(0.0, rule_score - anomaly_penalty)
    if anomaly is not None and anomaly > 0.5:
        reasons.append(
            f"anomaly: trajectory is in the top {max(1, round((1 - anomaly) * 50))}% "
            f"of atypical reference behavior (score {anomaly:.2f})"
        )
    return EpisodeScore(
        episode_index=episode_index,
        score=final,
        rule_score=rule_score,
        anomaly_score=anomaly,
        grade=grade_score(final, accept_at, reject_below),
        reasons=reasons,
    )
