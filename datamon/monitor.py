"""High-level, cached orchestration for dataset and dashboard analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional

import pandas as pd

from datamon.episode_quality import Flag, flags_for_episode
from datamon.frame_quality import DetectorConfig, FrameReport, analyze_frames
from datamon.frames import Episode, load_episode_file, load_parquet
from datamon.scoring import (
    AnomalyModel,
    EpisodeScore,
    episode_feature_vector,
    fit_anomaly_model,
    score_episode,
)


@dataclass
class MonitorResult:
    episode: Episode
    frame_report: FrameReport
    score: EpisodeScore
    episode_flags: List[Flag]


class Monitor:
    """Analyze a non-empty set of uniquely identified robot episodes."""

    def __init__(
        self,
        episodes: List[Episode],
        fps: Optional[float] = None,
        detector_config: Optional[DetectorConfig] = None,
        accept_at: float = 80.0,
        reject_below: float = 55.0,
    ):
        if not episodes:
            raise ValueError("monitor requires at least one episode")
        ids = [episode.episode_index for episode in episodes]
        if len(ids) != len(set(ids)):
            raise ValueError("episode_index values must be unique within a monitor")
        self.episodes = episodes
        self.fps = fps
        self.detector_config = detector_config or DetectorConfig()
        self.accept_at = accept_at
        self.reject_below = reject_below
        self._anomaly: Optional[AnomalyModel] = None
        self._by_index = {episode.episode_index: episode for episode in episodes}
        self._results: Dict[int, MonitorResult] = {}

    @classmethod
    def from_parquet(
        cls,
        path: Path,
        fps: Optional[float] = None,
        *,
        tasks_by_episode: Optional[Mapping[int, str]] = None,
        source: Optional[str] = None,
        **kwargs,
    ) -> "Monitor":
        episodes = load_parquet(
            Path(path), fps, tasks_by_episode=tasks_by_episode, source=source,
        )
        return cls(episodes, fps, **kwargs)

    @classmethod
    def from_episode_files(
        cls,
        paths: List[Path],
        fps: Optional[float] = None,
        *,
        tasks_by_episode: Optional[Mapping[int, str]] = None,
        source: Optional[str] = None,
        **kwargs,
    ) -> "Monitor":
        episodes = [
            load_episode_file(
                Path(path), fps,
                tasks_by_episode=tasks_by_episode,
                source=source or Path(path).parent.parent.parent.name,
            )
            for path in paths
        ]
        return cls(episodes, fps, **kwargs)

    def fit(self) -> "Monitor":
        """Calibrate anomaly scoring on episodes without hard integrity errors."""
        reference = []
        for episode in self.episodes:
            frame_report = analyze_frames(episode, config=self.detector_config)
            metadata = flags_for_episode(episode.episode_index, episode.task)
            if not frame_report.has_error() and not any(
                flag.severity.value == "error" for flag in metadata
            ):
                reference.append(episode)
        self._anomaly = fit_anomaly_model(reference)
        self._results.clear()
        return self

    def _anomaly_for(self, episode: Episode) -> Optional[float]:
        if self._anomaly is None:
            return None
        return self._anomaly.score(episode_feature_vector(episode))

    def get_episode(self, episode_index: int) -> Episode:
        return self._by_index[episode_index]

    def analyze_episode(self, episode_index: int) -> MonitorResult:
        if episode_index in self._results:
            return self._results[episode_index]
        episode = self._by_index[episode_index]
        frame_report = analyze_frames(episode, config=self.detector_config)
        metadata_flags = flags_for_episode(episode_index, episode.task)
        score = score_episode(
            episode_index,
            episode_flags=metadata_flags,
            frame_report=frame_report,
            anomaly=self._anomaly_for(episode),
            accept_at=self.accept_at,
            reject_below=self.reject_below,
        )
        result = MonitorResult(episode, frame_report, score, metadata_flags)
        self._results[episode_index] = result
        return result

    def analyze_all(self) -> List[MonitorResult]:
        return [self.analyze_episode(episode.episode_index) for episode in self.episodes]

    def summary_table(self) -> pd.DataFrame:
        rows = []
        for result in self.analyze_all():
            flags = result.frame_report.flags + result.episode_flags
            rows.append({
                "episode": result.episode.episode_index,
                "task": result.episode.task or "(missing)",
                "frames": result.episode.n_frames,
                "score": round(result.score.score, 1),
                "grade": result.score.grade,
                "anomaly": (
                    round(result.score.anomaly_score, 3)
                    if result.score.anomaly_score is not None else None
                ),
                "n_flags": sum(flag.severity.value != "info" for flag in flags),
            })
        return pd.DataFrame(rows).sort_values("score").reset_index(drop=True)

    def grade_counts(self) -> Dict[str, int]:
        counts = {"good": 0, "review": 0, "reject": 0}
        for result in self.analyze_all():
            counts[result.score.grade] += 1
        return counts

    def stream_episode(self, episode_index: int) -> Iterator[dict]:
        episode = self._by_index[episode_index]
        nominal_dt = (1.0 / episode.fps) if episode.fps else None
        previous_time = None
        for position in range(episode.n_frames):
            timestamp = float(episode.timestamp[position])
            interval = None if previous_time is None else timestamp - previous_time
            interval_ok = True
            if interval is not None and nominal_dt:
                interval_ok = (
                    abs(interval - nominal_dt) / nominal_dt
                    <= self.detector_config.jitter_tolerance
                )
            previous_time = timestamp
            yield {
                "frame": int(episode.frame_index[position]),
                "timestamp": timestamp,
                "state": episode.state[position],
                "action": episode.action[position],
                "interval": interval,
                "interval_ok": interval_ok,
            }
