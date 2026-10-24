"""Bounded live frame ingestion with immediate integrity feedback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

from datamon.frames import Episode
from datamon.gate import AdmitResult, IngestGate


@dataclass
class LiveFrameFeedback:
    frame_index: int
    ok: bool
    warnings: List[str] = field(default_factory=list)


class StreamIngestor:
    """Buffer exactly one bounded episode, then submit it to an ingest gate."""

    def __init__(
        self,
        gate: IngestGate,
        fps: float,
        on_frame: Optional[Callable[[LiveFrameFeedback], None]] = None,
        on_episode: Optional[Callable[[AdmitResult], None]] = None,
        max_frames: int = 100_000,
    ):
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError("fps must be a positive finite number")
        if max_frames < 1:
            raise ValueError("max_frames must be at least 1")
        self.gate = gate
        self.fps = float(fps)
        self.nominal_dt = 1.0 / self.fps
        self.on_frame = on_frame
        self.on_episode = on_episode
        self.max_frames = max_frames
        self._reset()

    def _reset(self) -> None:
        self._states: List[np.ndarray] = []
        self._actions: List[np.ndarray] = []
        self._timestamps: List[float] = []
        self._frame_indices: List[int] = []
        self._episode_index: Optional[int] = None
        self._task: Optional[str] = None
        self._task_index: Optional[int] = None
        self._source = "live"
        self._last_time: Optional[float] = None
        self._last_frame_index: Optional[int] = None
        self._state_width: Optional[int] = None
        self._action_width: Optional[int] = None

    def push_frame(
        self,
        episode_index: int,
        frame_index: int,
        timestamp: float,
        state: np.ndarray,
        action: np.ndarray,
        *,
        task: Optional[str] = None,
        task_index: Optional[int] = None,
        source: str = "live",
    ) -> LiveFrameFeedback:
        """Feed one frame and return warnings immediately."""
        if len(self._states) >= self.max_frames:
            raise ValueError(f"episode exceeds the {self.max_frames:,}-frame stream limit")
        episode_value = float(episode_index)
        frame_value = float(frame_index)
        if not np.isfinite(episode_value) or not episode_value.is_integer():
            raise ValueError("episode_index must be a finite integer")
        if not np.isfinite(frame_value) or not frame_value.is_integer():
            raise ValueError("frame_index must be a finite integer")
        episode_index = int(episode_value)
        frame_index = int(frame_value)
        timestamp = float(timestamp)
        state = np.asarray(state, dtype=np.float64)
        action = np.asarray(action, dtype=np.float64)
        if state.ndim != 1 or action.ndim != 1 or not state.size or not action.size:
            raise ValueError("state and action frames must be non-empty vectors")

        if self._episode_index is None:
            self._episode_index = episode_index
            self._task = str(task).strip() if task else None
            self._task_index = int(task_index) if task_index is not None else None
            self._source = str(source or "live")
            self._state_width = state.size
            self._action_width = action.size
        elif episode_index != self._episode_index:
            raise ValueError(
                f"received episode {episode_index} while episode "
                f"{self._episode_index} is still open"
            )
        if state.size != self._state_width or action.size != self._action_width:
            raise ValueError("state/action vector width changed during the episode")

        warnings: List[str] = []
        if self._last_frame_index is None:
            if frame_index != 0:
                warnings.append(f"stream starts at frame {frame_index}, expected 0")
        elif frame_index != self._last_frame_index + 1:
            delta = frame_index - self._last_frame_index
            if delta > 1:
                warnings.append(f"{delta - 1} frame(s) dropped before index {frame_index}")
            elif delta == 0:
                warnings.append(f"duplicate frame index {frame_index}")
            else:
                warnings.append(f"frame index moved backward to {frame_index}")

        if not np.isfinite(timestamp):
            warnings.append("non-finite timestamp")
        elif self._last_time is not None and np.isfinite(self._last_time):
            interval = timestamp - self._last_time
            tolerance = self.gate.config.detector.jitter_tolerance
            if interval <= 0 or abs(interval - self.nominal_dt) / self.nominal_dt > tolerance:
                warnings.append(
                    f"bad interval {interval * 1000:.0f} ms "
                    f"(expected {self.nominal_dt * 1000:.0f} ms)"
                )
        if not (np.isfinite(state).all() and np.isfinite(action).all()):
            warnings.append("non-finite value in state/action")

        self._states.append(state)
        self._actions.append(action)
        self._timestamps.append(timestamp)
        self._frame_indices.append(frame_index)
        self._last_time = timestamp
        self._last_frame_index = frame_index

        feedback = LiveFrameFeedback(frame_index, ok=not warnings, warnings=warnings)
        if self.on_frame:
            self.on_frame(feedback)
        return feedback

    def discard(self) -> None:
        """Drop the buffered partial episode without gating or storing it."""
        self._reset()

    def end_episode(self) -> Optional[AdmitResult]:
        """Gate the completed episode and always clear the stream buffer."""
        if not self._states:
            return None
        episode = Episode(
            episode_index=self._episode_index or 0,
            timestamp=np.array(self._timestamps),
            frame_index=np.array(self._frame_indices),
            state=np.vstack(self._states),
            action=np.vstack(self._actions),
            fps=self.fps,
            task=self._task,
            task_index=self._task_index,
            source=self._source,
        )
        try:
            result = self.gate.admit(episode)
            if self.on_episode:
                self.on_episode(result)
            return result
        finally:
            self._reset()

    def replay_episode(self, episode: Episode) -> AdmitResult:
        for position in range(episode.n_frames):
            self.push_frame(
                episode.episode_index,
                int(episode.frame_index[position]),
                float(episode.timestamp[position]),
                episode.state[position],
                episode.action[position],
                task=episode.task,
                task_index=episode.task_index,
                source=episode.source,
            )
        result = self.end_episode()
        assert result is not None
        return result
