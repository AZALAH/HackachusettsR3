"""Transport-agnostic collector adapter feeding the bounded ingest stream.

A real deployment acquires frames from ROS 2, a WebSocket, or a robot SDK
callback. Those transports differ, but the quality pipeline must not: this
module is the single boundary a transport plugs into, so ``stream.py``,
``gate.py``, and the detectors never learn how frames arrive.

The adapter owns three policies a live transport forces on us and a file loader
never sees:

* **backpressure** — an acquisition thread can produce frames faster than the
  gate consumes them. A bounded queue absorbs bursts; when it overflows the
  policy either drops the oldest frame (and counts it, so the gate's
  dropped-frame check still fires on the resulting index gap) or signals the
  producer to stop.
* **partial episode** — a transport can stop mid-episode. On disconnect a
  partial is finalized only when it already holds enough frames to be worth
  scoring; otherwise it is discarded so a truncated demonstration never reaches
  training.
* **disconnect** — a clean ``disconnect`` flushes the open episode through the
  gate; a hard ``abort`` drops it.

Nothing here imports a transport library. A ROS 2 subscription callback, a
WebSocket ``on_message`` handler, or an SDK poll loop calls :meth:`submit` with
one frame; the adapter does the rest.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Deque, List, Optional

import numpy as np

from datamon.gate import AdmitResult, IngestGate
from datamon.stream import LiveFrameFeedback, StreamIngestor


class BackpressurePolicy(str, Enum):
    """What to do when the ingest queue is full."""

    DROP_OLDEST = "drop_oldest"
    BLOCK_PRODUCER = "block_producer"


@dataclass
class Frame:
    """One acquired frame, independent of how it arrived."""

    episode_index: int
    frame_index: int
    timestamp: float
    state: np.ndarray
    action: np.ndarray
    task: Optional[str] = None
    task_index: Optional[int] = None
    source: str = "collector"


@dataclass
class CollectorStats:
    frames_submitted: int = 0
    frames_ingested: int = 0
    frames_dropped_backpressure: int = 0
    episodes_completed: int = 0
    partials_discarded: int = 0
    partials_salvaged: int = 0


class CollectorAdapter:
    """Bridge a live transport to a single bounded :class:`StreamIngestor`.

    The adapter is thread-safe for submission: a transport may call
    :meth:`submit` from an acquisition thread while the consumer drains on
    another. It buffers one episode at a time, matching the stream's
    single-episode contract.
    """

    def __init__(
        self,
        gate: IngestGate,
        fps: float,
        *,
        max_queue: int = 512,
        backpressure: BackpressurePolicy = BackpressurePolicy.DROP_OLDEST,
        min_frames_on_disconnect: int = 5,
        on_episode: Optional[Callable[[AdmitResult], None]] = None,
        on_frame: Optional[Callable[[LiveFrameFeedback], None]] = None,
    ):
        if max_queue < 1:
            raise ValueError("max_queue must be at least 1")
        if min_frames_on_disconnect < 1:
            raise ValueError("min_frames_on_disconnect must be at least 1")
        self._ingestor = StreamIngestor(
            gate, fps=fps, on_frame=on_frame, on_episode=self._record_episode,
        )
        self._user_on_episode = on_episode
        self.max_queue = int(max_queue)
        self.backpressure = backpressure
        self.min_frames_on_disconnect = int(min_frames_on_disconnect)
        self.stats = CollectorStats()
        self._queue: Deque[Frame] = deque()
        self._lock = threading.Lock()
        self._open_episode: Optional[int] = None
        self._buffered_frames = 0

    # -- producer side -------------------------------------------------------

    def submit(self, frame: Frame) -> bool:
        """Enqueue one acquired frame.

        Returns ``True`` when accepted, ``False`` when a ``BLOCK_PRODUCER``
        policy rejected it because the queue is full (the producer should slow
        down or retry). ``DROP_OLDEST`` always accepts, dropping and counting
        the oldest queued frame to make room.
        """
        with self._lock:
            if len(self._queue) >= self.max_queue:
                if self.backpressure is BackpressurePolicy.BLOCK_PRODUCER:
                    return False
                self._queue.popleft()
                self.stats.frames_dropped_backpressure += 1
            self._queue.append(frame)
            self.stats.frames_submitted += 1
            return True

    # -- consumer side -------------------------------------------------------

    def drain(self) -> List[AdmitResult]:
        """Push every queued frame into the stream, gating finished episodes.

        A frame whose episode differs from the one currently open closes the
        open episode first (a new episode id is the collector's end-of-episode
        signal), then starts the new one.
        """
        results: List[AdmitResult] = []
        while True:
            with self._lock:
                if not self._queue:
                    break
                frame = self._queue.popleft()

            if (self._open_episode is not None
                    and frame.episode_index != self._open_episode):
                finished = self._finalize(discard_if_short=False)
                if finished is not None:
                    results.append(finished)

            self._ingestor.push_frame(
                frame.episode_index,
                frame.frame_index,
                frame.timestamp,
                frame.state,
                frame.action,
                task=frame.task,
                task_index=frame.task_index,
                source=frame.source,
            )
            self._open_episode = frame.episode_index
            self._buffered_frames += 1
            self.stats.frames_ingested += 1
        return results

    def disconnect(self) -> Optional[AdmitResult]:
        """Transport closed cleanly: drain, then flush a salvageable partial."""
        self.drain()
        return self._finalize(discard_if_short=True)

    def abort(self) -> None:
        """Transport failed: discard the open episode and any queued frames."""
        with self._lock:
            self._queue.clear()
        if self._open_episode is not None and self._buffered_frames:
            self.stats.partials_discarded += 1
        self._ingestor.discard()  # clears the stream buffer without gating
        self._reset_open()

    # -- internals -----------------------------------------------------------

    def _finalize(self, *, discard_if_short: bool) -> Optional[AdmitResult]:
        if self._open_episode is None or self._buffered_frames == 0:
            self._reset_open()
            return None
        if discard_if_short and self._buffered_frames < self.min_frames_on_disconnect:
            self.stats.partials_discarded += 1
            self._ingestor.discard()  # too short: drop without gating
            self._reset_open()
            return None
        if discard_if_short:
            self.stats.partials_salvaged += 1
        result = self._ingestor.end_episode()
        self._reset_open()
        return result

    def _record_episode(self, result: AdmitResult) -> None:
        self.stats.episodes_completed += 1
        if self._user_on_episode:
            self._user_on_episode(result)

    def _reset_open(self) -> None:
        self._open_episode = None
        self._buffered_frames = 0
