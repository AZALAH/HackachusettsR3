"""Content-addressed ingest gate that isolates clean, review, and rejected data."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from datamon.episode_quality import Flag, flags_for_episode
from datamon.frame_quality import DetectorConfig, FrameReport, analyze_frames
from datamon.frames import Episode, load_episode_file
from datamon.scoring import (
    AnomalyModel,
    EpisodeScore,
    episode_feature_vector,
    fit_anomaly_model,
    score_episode,
)


class Decision(str, Enum):
    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


class OperatorAction(str, Enum):
    """Why a manifest event exists.

    ``AUTOMATED`` is the gate's own routing decision. The rest are human review
    actions recorded on top of an existing content ID without discarding its
    history.
    """

    AUTOMATED = "automated"
    PROMOTE = "operator_promote"
    REJECT = "operator_reject"
    RECOLLECT = "operator_recollect"


@dataclass(frozen=True)
class GateConfig:
    accept_at: float = 80.0
    reject_below: float = 55.0
    min_frames: int = 5
    require_task: bool = True
    hard_reject_checks: tuple[str, ...] = (
        "dropped_frames", "out_of_range", "missing_label", "garbage_label",
    )
    detector: DetectorConfig = field(default_factory=DetectorConfig)

    def __post_init__(self) -> None:
        if not 0 <= self.reject_below <= self.accept_at <= 100:
            raise ValueError(
                "thresholds must satisfy 0 <= reject_below <= accept_at <= 100"
            )
        if self.min_frames < 1:
            raise ValueError("min_frames must be at least 1")


@dataclass
class AdmitResult:
    episode_index: int
    decision: Decision
    score: EpisodeScore
    frame_report: FrameReport
    episode_flags: List[Flag]
    reasons: List[str] = field(default_factory=list)
    stored_path: Optional[str] = None
    ingest_id: Optional[str] = None
    source: str = "unknown"
    fps: Optional[float] = None
    action: OperatorAction = OperatorAction.AUTOMATED
    note: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "ts": time.time(),
            "ingest_id": self.ingest_id,
            "source": self.source,
            "episode_index": self.episode_index,
            "frame_count": self.frame_report.n_frames,
            "decision": self.decision.value,
            "score": round(self.score.score, 1),
            "grade": self.score.grade,
            "anomaly_score": self.score.anomaly_score,
            "reasons": self.reasons,
            "stored_path": self.stored_path,
            "fps": self.fps,
            "action": self.action.value,
            "note": self.note,
        }


class IngestGate:
    """Evaluate and persist the exact episode that was scored.

    Files are content-addressed and source-namespaced. Re-evaluating identical
    content cannot overwrite another episode, and a changed decision removes the
    older routed copy before the new manifest event is appended.
    """

    def __init__(
        self,
        root: Path,
        config: Optional[GateConfig] = None,
        anomaly_model: Optional[AnomalyModel] = None,
    ):
        self.root = Path(root)
        self.config = config or GateConfig()
        self.anomaly_model = anomaly_model
        self.dirs = {
            Decision.ACCEPT: self.root / "clean",
            Decision.REVIEW: self.root / "review",
            Decision.REJECT: self.root / "quarantine",
        }
        for directory in self.dirs.values():
            directory.mkdir(parents=True, exist_ok=True)
        self.manifest = self.root / "manifest.jsonl"
        self._lock = threading.Lock()

    def calibrate(self, reference_episodes: List[Episode]) -> "IngestGate":
        """Fit anomaly scoring only on reference episodes without hard errors."""
        clean = []
        for episode in reference_episodes:
            frame_report = analyze_frames(episode, config=self.config.detector)
            metadata = self._episode_flags(episode)
            if frame_report.has_error() or any(flag.severity.value == "error"
                                               for flag in metadata):
                continue
            clean.append(episode)
        self.anomaly_model = fit_anomaly_model(clean)
        return self

    def _episode_flags(self, episode: Episode) -> List[Flag]:
        if not self.config.require_task and episode.task is None:
            return []
        return flags_for_episode(episode.episode_index, episode.task)

    def evaluate(self, episode: Episode) -> AdmitResult:
        frame_report = analyze_frames(episode, config=self.config.detector)
        episode_flags = self._episode_flags(episode)
        anomaly = (
            self.anomaly_model.score(episode_feature_vector(episode))
            if self.anomaly_model else None
        )
        score = score_episode(
            episode.episode_index,
            episode_flags=episode_flags,
            frame_report=frame_report,
            anomaly=anomaly,
            accept_at=self.config.accept_at,
            reject_below=self.config.reject_below,
        )
        decision, reasons = self._decide(episode, frame_report, episode_flags, score)
        return AdmitResult(
            episode_index=episode.episode_index,
            decision=decision,
            score=score,
            frame_report=frame_report,
            episode_flags=episode_flags,
            reasons=reasons,
            source=episode.source,
            fps=episode.fps,
        )

    def admit(self, episode: Episode) -> AdmitResult:
        """Evaluate, atomically store the normalized episode, and audit the result."""
        result = self.evaluate(episode)
        ingest_id = self._episode_digest(episode)
        source = self._safe_source(episode.source)
        filename = f"episode_{episode.episode_index:06d}_{ingest_id[:12]}.parquet"
        destination = self.dirs[result.decision] / source / filename

        with self._lock:
            self._write_episode(episode, destination)
            self._remove_other_routes(ingest_id, destination)
            result.ingest_id = ingest_id
            result.stored_path = str(destination)
            self._log(result)
        return result

    def _decide(
        self,
        episode: Episode,
        frame_report: FrameReport,
        episode_flags: List[Flag],
        score: EpisodeScore,
    ) -> tuple[Decision, List[str]]:
        reasons = list(score.reasons)
        if episode.n_frames < self.config.min_frames:
            reasons.insert(
                0, f"only {episode.n_frames} frames (< {self.config.min_frames})",
            )
            return Decision.REJECT, reasons
        all_flags = list(frame_report.flags) + list(episode_flags)
        hard = [flag for flag in all_flags
                if flag.check in self.config.hard_reject_checks
                and flag.severity.value == "error"]
        if hard:
            reasons.insert(0, f"integrity failure: {hard[0].check} — {hard[0].reason}")
            return Decision.REJECT, reasons
        if score.score >= self.config.accept_at:
            return Decision.ACCEPT, reasons
        if score.score < self.config.reject_below:
            return Decision.REJECT, reasons
        return Decision.REVIEW, reasons

    @staticmethod
    def _safe_source(source: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", source.strip()).strip(".-")
        return safe or "unknown"

    @staticmethod
    def _episode_digest(episode: Episode) -> str:
        digest = hashlib.sha256()
        for value in (
            episode.source, str(episode.episode_index), episode.task or "",
            str(episode.task_index), str(episode.fps),
        ):
            digest.update(value.encode("utf-8"))
            digest.update(b"\0")
        for array in (episode.timestamp, episode.frame_index, episode.state, episode.action):
            contiguous = np.ascontiguousarray(array)
            digest.update(str(contiguous.shape).encode("ascii"))
            digest.update(contiguous.dtype.str.encode("ascii"))
            digest.update(contiguous.tobytes())
        return digest.hexdigest()

    @staticmethod
    def _write_episode(episode: Episode, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "observation.state": list(episode.state),
            "action": list(episode.action),
            "timestamp": episode.timestamp,
            "frame_index": episode.frame_index,
            "episode_index": np.full(episode.n_frames, episode.episode_index),
        }
        if episode.task is not None:
            payload["task"] = np.full(episode.n_frames, episode.task, dtype=object)
        if episode.task_index is not None:
            payload["task_index"] = np.full(episode.n_frames, episode.task_index)
        frame = pd.DataFrame(payload)
        temporary = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            frame.to_parquet(temporary, index=False)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _remove_other_routes(self, ingest_id: str, keep: Path) -> None:
        pattern = f"*_{ingest_id[:12]}.parquet"
        for root in self.dirs.values():
            for path in root.rglob(pattern):
                if path != keep:
                    path.unlink(missing_ok=True)

    def _log(self, result: AdmitResult) -> None:
        with self.manifest.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.as_dict(), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _latest_records(self) -> Dict[str, dict]:
        latest: Dict[str, dict] = {}
        if not self.manifest.exists():
            return latest
        with self.manifest.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                ingest_id = record.get("ingest_id")
                if ingest_id:
                    latest[ingest_id] = record
        return latest

    def stats(self) -> Dict[str, int]:
        counts = {decision.value: 0 for decision in Decision}
        for record in self._latest_records().values():
            decision = record.get("decision")
            if decision in counts:
                counts[decision] += 1
        return counts

    def review_queue(self) -> List[dict]:
        """Latest record for every content ID currently routed to review.

        Sorted worst-first so an operator sees the most doubtful episodes at the
        top of the queue.
        """
        pending = [
            record for record in self._latest_records().values()
            if record.get("decision") == Decision.REVIEW.value
        ]
        pending.sort(key=lambda record: record.get("score", 0.0))
        return pending

    def history(self, ingest_id: str) -> List[dict]:
        """Every manifest event for one content ID, oldest first."""
        events: List[dict] = []
        if not self.manifest.exists():
            return events
        with self.manifest.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if record.get("ingest_id") == ingest_id:
                    events.append(record)
        return events

    def operator_decision(
        self,
        ingest_id: str,
        action: OperatorAction,
        note: Optional[str] = None,
    ) -> AdmitResult:
        """Apply a human review decision to an already-gated episode.

        The exact stored episode is reconstructed from its content-addressed
        parquet and its original scores are preserved; only the route and the
        audit trail change. ``PROMOTE`` moves it to clean, ``REJECT`` to
        quarantine, and ``RECOLLECT`` keeps it in review while recording that
        recollection was requested. Prior history is never rewritten; a new
        event is appended so the manifest shows who changed the route and why.
        """
        if action is OperatorAction.AUTOMATED:
            raise ValueError("operator_decision requires a human review action")

        with self._lock:
            current = self._latest_records().get(ingest_id)
            if current is None:
                raise KeyError(f"unknown ingest_id: {ingest_id}")
            if current.get("decision") != Decision.REVIEW.value:
                raise ValueError(
                    f"ingest_id {ingest_id[:12]} is not in review "
                    f"(current route: {current.get('decision')})"
                )

            stored_path = current.get("stored_path")
            if not stored_path or not Path(stored_path).is_file():
                raise FileNotFoundError(
                    f"stored episode for {ingest_id[:12]} is missing on disk"
                )
            episode = load_episode_file(
                Path(stored_path), fps=current.get("fps")
            )

            result = self.evaluate(episode)
            if action is OperatorAction.PROMOTE:
                result.decision = Decision.ACCEPT
            elif action is OperatorAction.REJECT:
                result.decision = Decision.REJECT
            else:  # RECOLLECT keeps the item in the review route.
                result.decision = Decision.REVIEW
            result.action = action
            result.note = (note or "").strip() or None
            result.ingest_id = ingest_id
            result.source = current.get("source", episode.source)

            source = self._safe_source(result.source)
            filename = (
                f"episode_{episode.episode_index:06d}_{ingest_id[:12]}.parquet"
            )
            destination = self.dirs[result.decision] / source / filename
            self._write_episode(episode, destination)
            self._remove_other_routes(ingest_id, destination)
            result.stored_path = str(destination)
            self._log(result)
        return result

    def wasted_frames_prevented(self) -> int:
        return sum(
            int(record.get("frame_count") or 0)
            for record in self._latest_records().values()
            if record.get("decision") == Decision.REJECT.value
        )
