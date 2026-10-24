"""Named per-robot profiles for channel roles, ranges, and detector thresholds.

Generic ``state_0`` / ``action_0`` channel names are fine for the demo but weak
for real operator feedback: a flatline on the gripper DOF is expected, a flatline
on a wrist joint is a fault, and the detector cannot tell them apart without the
rig's layout. A :class:`RobotProfile` captures that rig knowledge once — expected
capture rate, human-readable channel roles, physical ranges, the channels allowed
to stay static, and the task family — and :class:`ProfileStore` persists named
profiles so an operator picks a rig instead of re-typing thresholds every session.

A profile is pure configuration. ``to_detector_config()`` projects it onto the
existing :class:`DetectorConfig`, so nothing downstream of the detector changes.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from datamon.frame_quality import DetectorConfig

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")


@dataclass
class RobotProfile:
    """Everything the quality pipeline should know about one rig."""

    name: str
    fps: float = 15.0
    jitter_tolerance: float = 0.25
    cadence_tolerance: float = 0.25
    # Maps a channel name (e.g. "state_0") to a human role (e.g. "shoulder_pan").
    channel_roles: Dict[str, str] = field(default_factory=dict)
    # Hard physical bounds per channel; non-finite values are always rejected.
    ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    # Channels expected to stay constant (unused DOFs, a closed gripper).
    allowed_static_channels: List[str] = field(default_factory=list)
    task_family: Optional[str] = None

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name or ""):
            raise ValueError(
                "profile name must be 1-64 chars of letters, digits, space, _ . or -"
            )
        self.fps = float(self.fps)
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        for field_name in ("jitter_tolerance", "cadence_tolerance"):
            value = float(getattr(self, field_name))
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")
            setattr(self, field_name, value)
        normalized: Dict[str, Tuple[float, float]] = {}
        for channel, bounds in self.ranges.items():
            pair = tuple(float(value) for value in bounds)
            if len(pair) != 2 or pair[0] >= pair[1]:
                raise ValueError(f"invalid range for {channel}: {bounds!r}")
            normalized[str(channel)] = pair
        self.ranges = normalized
        self.allowed_static_channels = [str(c) for c in self.allowed_static_channels]
        if self.task_family is not None:
            self.task_family = str(self.task_family).strip() or None

    def to_detector_config(self) -> DetectorConfig:
        """Project this profile onto the detector's tunable thresholds."""
        return DetectorConfig(
            jitter_tolerance=self.jitter_tolerance,
            cadence_tolerance=self.cadence_tolerance,
            ranges=dict(self.ranges),
            allowed_static_channels=frozenset(self.allowed_static_channels),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RobotProfile":
        ranges = {
            channel: tuple(bounds)
            for channel, bounds in (data.get("ranges") or {}).items()
        }
        return cls(
            name=data["name"],
            fps=data.get("fps", 15.0),
            jitter_tolerance=data.get("jitter_tolerance", 0.25),
            cadence_tolerance=data.get("cadence_tolerance", 0.25),
            channel_roles=dict(data.get("channel_roles") or {}),
            ranges=ranges,
            allowed_static_channels=list(data.get("allowed_static_channels") or []),
            task_family=data.get("task_family"),
        )


class ProfileStore:
    """Persist named robot profiles to a single JSON file.

    Keyed by profile name; saving an existing name overwrites it. Writes are
    atomic (temp file + ``os.replace``) so a crash never leaves a half-written
    store, matching the durability stance of the ingest manifest.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> Dict[str, dict]:
        if not self.path.is_file():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, data: Dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def save(self, profile: RobotProfile) -> RobotProfile:
        data = self._read()
        data[profile.name] = profile.to_dict()
        self._write(data)
        return profile

    def get(self, name: str) -> RobotProfile:
        data = self._read()
        if name not in data:
            raise KeyError(f"unknown profile: {name}")
        return RobotProfile.from_dict(data[name])

    def names(self) -> List[str]:
        return sorted(self._read().keys())

    def all(self) -> List[RobotProfile]:
        return [RobotProfile.from_dict(entry) for entry in self._read().values()]

    def delete(self, name: str) -> bool:
        data = self._read()
        if name not in data:
            return False
        del data[name]
        self._write(data)
        return True
