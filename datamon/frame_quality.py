"""Frame-level stream quality checks for a single robot episode.

Directly addresses R3's named problems on the real sensor/action stream:

  dropped_frames  — gaps in frame_index, or timestamp jumps > ~1.5 nominal steps
  timing_drift    — frame interval drifts / jitters vs the nominal 1/fps
  sensor_noise    — a channel's high-frequency content is abnormally large
  saturation      — a channel pinned at its min/max (clipping) for a run of frames
  stuck_channel   — a channel that stops changing (flatline / repeated values)
  out_of_range    — NaN/Inf or values outside a configured sane range

Results are FrameFlags (same shape as episode flags) plus a per-channel/per-frame
health breakdown the dashboard can plot. Everything is explainable: each flag
says which channel/frame and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

from datamon.frames import Episode


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class FrameFlag:
    episode_index: int
    check: str
    severity: Severity
    reason: str
    channel: Optional[str] = None
    frame: Optional[int] = None

    def as_dict(self) -> dict:
        return {
            "episode_index": self.episode_index,
            "check": self.check,
            "severity": self.severity.value,
            "reason": self.reason,
            "channel": self.channel,
            "frame": self.frame,
        }


EPS = 1e-9


@dataclass(frozen=True)
class DetectorConfig:
    """Operator-tunable detector thresholds passed through every analysis path."""

    jitter_tolerance: float = 0.25
    cadence_tolerance: float = 0.25
    ranges: Dict[str, tuple] = field(default_factory=dict)
    allowed_static_channels: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for name, value in (
            ("jitter_tolerance", self.jitter_tolerance),
            ("cadence_tolerance", self.cadence_tolerance),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for channel, bounds in self.ranges.items():
            if len(bounds) != 2 or bounds[0] >= bounds[1]:
                raise ValueError(f"invalid range for {channel}: {bounds!r}")


# --- timing checks ---------------------------------------------------------

def check_dropped_frames(ep: Episode, nominal_dt: Optional[float] = None) -> List[FrameFlag]:
    """Detect missing, duplicate, backward, and timestamp-gap frames."""
    flags: List[FrameFlag] = []
    fi = ep.frame_index
    if len(fi) == 0:
        return [FrameFlag(ep.episode_index, "dropped_frames", Severity.ERROR,
                          "episode contains no frames")]
    if fi[0] != 0:
        flags.append(FrameFlag(
            ep.episode_index, "dropped_frames", Severity.ERROR,
            f"frame sequence starts at {fi[0]}, expected 0", frame=int(fi[0]),
        ))

    frame_diffs = np.diff(fi)
    for position in np.where(frame_diffs != 1)[0]:
        before, after = int(fi[position]), int(fi[position + 1])
        delta = int(frame_diffs[position])
        if delta > 1:
            reason = f"{delta - 1} frame(s) missing between index {before} and {after}"
        elif delta == 0:
            reason = f"duplicate frame index {after}"
        else:
            reason = f"frame index moves backward from {before} to {after}"
        flags.append(FrameFlag(
            ep.episode_index, "dropped_frames", Severity.ERROR,
            reason, frame=before,
        ))

    dt = nominal_dt or _nominal_dt(ep)
    if dt and np.isfinite(dt) and dt > 0 and len(ep.timestamp) > 1:
        time_diffs = np.diff(ep.timestamp)
        for position in np.where(np.isfinite(time_diffs) & (time_diffs > 1.5 * dt))[0]:
            # Avoid reporting one physical loss twice when frame_index already shows it.
            if frame_diffs[position] != 1:
                continue
            missed = max(1, int(round(time_diffs[position] / dt)) - 1)
            frame = int(fi[position])
            flags.append(FrameFlag(
                ep.episode_index, "dropped_frames", Severity.ERROR,
                f"timestamp gap {time_diffs[position] * 1000:.0f} ms after frame "
                f"{frame} (~{missed} frame(s) at {1 / dt:.0f} fps)",
                frame=frame,
            ))
    return flags


def check_timing_drift(
    ep: Episode,
    nominal_dt: Optional[float] = None,
    jitter_tol: float = 0.25,
    cadence_tol: Optional[float] = None,
) -> List[FrameFlag]:
    """Flag wrong capture cadence, interval jitter, and systematic drift."""
    if len(ep.timestamp) < 3:
        return []
    dt = nominal_dt or _nominal_dt(ep)
    if not dt or not np.isfinite(dt) or dt <= 0:
        return []
    time_diffs = np.diff(ep.timestamp)
    if not np.isfinite(time_diffs).all() or np.any(time_diffs <= 0):
        return []  # integrity checks report these more directly

    cadence_tol = jitter_tol if cadence_tol is None else cadence_tol
    median_dt = float(np.median(time_diffs))
    cadence_error = abs(median_dt - dt) / dt
    jitter = float(np.std(time_diffs - median_dt) / dt)
    flags: List[FrameFlag] = []
    if cadence_error > cadence_tol:
        flags.append(FrameFlag(
            ep.episode_index, "timing_drift", Severity.WARN,
            f"median interval is {median_dt * 1000:.0f} ms, "
            f"{cadence_error * 100:.0f}% from expected {dt * 1000:.0f} ms",
        ))
    if jitter > jitter_tol:
        flags.append(FrameFlag(
            ep.episode_index, "timing_drift", Severity.WARN,
            f"interval jitter {jitter * 100:.0f}% of nominal "
            f"(tolerance {jitter_tol * 100:.0f}%)",
        ))
    if len(time_diffs) >= 10:
        third = max(1, len(time_diffs) // 3)
        first = float(np.mean(time_diffs[:third]))
        last = float(np.mean(time_diffs[-third:]))
        drift = (last - first) / dt
        if abs(drift) > jitter_tol:
            flags.append(FrameFlag(
                ep.episode_index, "timing_drift", Severity.WARN,
                f"interval drifts {drift * 100:+.0f}% from start to end of episode",
            ))
    return flags


def _nominal_dt(ep: Episode) -> Optional[float]:
    if ep.fps:
        return 1.0 / ep.fps
    if len(ep.timestamp) > 1:
        diffs = np.diff(ep.timestamp)
        valid = diffs[np.isfinite(diffs) & (diffs > 0)]
        return float(np.median(valid)) if valid.size else None
    return None


# --- signal checks ---------------------------------------------------------

def _discrete_channels(X: np.ndarray, max_levels: int = 3) -> np.ndarray:
    """Boolean mask of channels that take only a few distinct values (e.g. a
    gripper open/close DOF). Such channels legitimately hold constant values, so
    stuck/saturation checks must not treat their held runs as data faults."""
    n_chan = X.shape[1]
    mask = np.zeros(n_chan, dtype=bool)
    for j in range(n_chan):
        col = X[:, j]
        finite = col[np.isfinite(col)]
        if finite.size == 0:
            continue  # all non-finite: let out_of_range handle it
        rng = np.ptp(finite)
        if rng < EPS:
            continue  # fully constant handled separately
        # quantize to the channel's range and count distinct levels
        q = np.round((finite - finite.min()) / (rng + EPS) * 20).astype(int)
        if len(np.unique(q)) <= max_levels:
            mask[j] = True
    return mask


def check_stuck_channels(ep: Episode, min_run: int = 5,
                         rel_eps: float = 1e-4,
                         min_fraction: float = 0.5,
                         rest_margin: float = 0.15,
                         allowed_static_channels: frozenset[str] = frozenset()) -> List[FrameFlag]:
    """Flag CONTINUOUS channels whose value FREEZES mid-activity.

    Two legitimate behaviors must NOT be flagged:
      * discrete/binary DOFs (grippers that snap between a few levels)
      * a channel holding at a RESTING extreme of its range (e.g. a gripper
        fully open at 0.0 between grasps) — holding at rest is normal

    A true stuck sensor freezes at an ACTIVE value (away from the channel's
    resting extremes) and stays there. So we flag a run only if it is long
    (>= min_fraction of the episode) AND the held value sits in the interior of
    the channel's range, not within `rest_margin` of either extreme.
    """
    X = ep.channels
    names = ep.channel_names()
    discrete = _discrete_channels(X)
    flags: List[FrameFlag] = []
    n = X.shape[0]
    for j, name in enumerate(names):
        if name in allowed_static_channels:
            continue
        if discrete[j]:
            continue  # grippers / binary DOFs hold values by design
        col = X[:, j]
        finite = col[np.isfinite(col)]
        if finite.size == 0:
            continue
        lo, hi = float(finite.min()), float(finite.max())
        rng = hi - lo
        scale = rng or 1.0
        same = np.abs(np.diff(col)) <= rel_eps * (abs(scale) + EPS)
        if same.all():
            flags.append(FrameFlag(
                ep.episode_index, "stuck_channel", Severity.WARN,
                f"{name} is constant for the whole episode", channel=name))
            continue
        # longest run of 'unchanged'
        longest, cur, start, best_start = 0, 0, 0, 0
        for i, s in enumerate(same):
            if s:
                if cur == 0:
                    start = i
                cur += 1
                if cur > longest:
                    longest, best_start = cur, start
            else:
                cur = 0
        run_len = longest + 1
        if not (run_len >= min_run and run_len < n and run_len >= min_fraction * n):
            continue
        # is the held value at a resting extreme? if so, it's a normal hold.
        held = float(col[best_start])
        if rng > EPS:
            norm = (held - lo) / rng
            at_rest = norm <= rest_margin or norm >= (1.0 - rest_margin)
            if at_rest:
                continue
        flags.append(FrameFlag(
            ep.episode_index, "stuck_channel", Severity.WARN,
            f"{name} froze mid-range at {held:.3f} for {run_len} frames "
            f"({run_len/n*100:.0f}% of episode, from frame {best_start})",
            channel=name, frame=best_start))
    return flags


def check_saturation(ep: Episode, min_run: int = 3,
                     clip_fraction: float = 0.6) -> List[FrameFlag]:
    """Flag channels that look CLIPPED against a hard limit (lost data).

    Distinguishing real clipping from a normal rest/hold:
      * discrete DOFs (grippers) are exempt
      * resting at a channel's MINIMUM (home/open) is normal, not clipping
      * true clipping pins MANY samples at the exact same ceiling for a large
        fraction of the episode — the sensor's dynamic range was exceeded and
        information was lost

    So we only flag the MAX edge, and only when the exact-value pin covers at
    least `clip_fraction` of the episode (a strong clipping signature), which
    avoids false alarms on ordinary holds.
    """
    X = ep.channels
    names = ep.channel_names()
    discrete = _discrete_channels(X)
    flags: List[FrameFlag] = []
    for j, name in enumerate(names):
        if discrete[j]:
            continue  # discrete DOFs (grippers) sit at their extremes by design
        col = X[:, j]
        finite = col[np.isfinite(col)]
        if finite.size == 0:
            continue
        lo, hi = float(finite.min()), float(finite.max())
        if hi - lo < EPS:
            continue
        at = np.isclose(col, hi, rtol=0, atol=1e-6)
        run = _longest_run(at)
        if run >= min_run and at.mean() >= clip_fraction:
            flags.append(FrameFlag(
                ep.episode_index, "saturation", Severity.WARN,
                f"{name} pinned at max ({hi:.3f}) for {run} frames "
                f"({at.mean()*100:.0f}% of episode) — looks clipped",
                channel=name))
    return flags


def check_out_of_range(ep: Episode,
                       ranges: Optional[Dict[str, tuple]] = None) -> List[FrameFlag]:
    """Flag invalid timing values and channels outside configured bounds."""
    flags: List[FrameFlag] = []
    bad_time = ~np.isfinite(ep.timestamp)
    if bad_time.any():
        position = int(np.argmax(bad_time))
        flags.append(FrameFlag(
            ep.episode_index, "out_of_range", Severity.ERROR,
            f"timestamp has {int(bad_time.sum())} non-finite value(s)",
            channel="timestamp", frame=int(ep.frame_index[position]),
        ))
    if len(ep.timestamp) > 1:
        invalid_order = np.where(np.diff(ep.timestamp) <= 0)[0]
        if invalid_order.size:
            position = int(invalid_order[0])
            flags.append(FrameFlag(
                ep.episode_index, "out_of_range", Severity.ERROR,
                "timestamps are duplicate or move backward",
                channel="timestamp", frame=int(ep.frame_index[position]),
            ))

    X = ep.channels
    names = ep.channel_names()
    for j, name in enumerate(names):
        col = X[:, j]
        bad = ~np.isfinite(col)
        if bad.any():
            position = int(np.argmax(bad))
            flags.append(FrameFlag(
                ep.episode_index, "out_of_range", Severity.ERROR,
                f"{name} has {int(bad.sum())} non-finite value(s)", channel=name,
                frame=int(ep.frame_index[position])))
        if ranges and name in ranges:
            lo, hi = ranges[name]
            oob = np.isfinite(col) & ((col < lo) | (col > hi))
            if oob.any():
                position = int(np.argmax(oob))
                flags.append(FrameFlag(
                    ep.episode_index, "out_of_range", Severity.ERROR,
                    f"{name} has {int(oob.sum())} value(s) outside [{lo}, {hi}]",
                    channel=name, frame=int(ep.frame_index[position])))
    return flags


def check_sensor_noise(ep: Episode, z_thresh: float = 4.0) -> List[FrameFlag]:
    """Flag channels whose high-frequency content is an outlier vs the others.

    Uses lag-1 difference energy as a proxy for noisiness, then a robust z-score
    across channels of the SAME kind (state vs action). A sensor that is far
    noisier than its peers is suspicious.
    """
    X = ep.channels
    names = ep.channel_names()
    if X.shape[0] < 4:
        return []
    # Non-finite values are handled by check_out_of_range; sanitize here so the
    # noise statistics stay valid and don't emit warnings on corrupt channels.
    Xf = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    hf = np.std(np.diff(Xf, axis=0), axis=0)  # per-channel hf energy
    # normalize by channel amplitude so large-range channels aren't auto-noisy
    amp = np.ptp(Xf, axis=0) + EPS
    noisiness = hf / amp

    flags: List[FrameFlag] = []
    for prefix in ("state_", "action_"):
        idx = [i for i, n in enumerate(names) if n.startswith(prefix)]
        if len(idx) < 3:
            continue
        vals = noisiness[idx]
        med = np.median(vals)
        mad = np.median(np.abs(vals - med)) or EPS
        for k, i in enumerate(idx):
            z = 0.6745 * (vals[k] - med) / mad
            if z > z_thresh:
                flags.append(FrameFlag(
                    ep.episode_index, "sensor_noise", Severity.WARN,
                    f"{names[i]} is unusually noisy vs peers (robust z={z:.1f})",
                    channel=names[i]))
    return flags


def _longest_run(mask: np.ndarray) -> int:
    longest = cur = 0
    for v in mask:
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    return longest


# --- orchestration ---------------------------------------------------------

@dataclass
class FrameReport:
    episode_index: int
    n_frames: int
    flags: List[FrameFlag] = field(default_factory=list)

    def counts_by_check(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for f in self.flags:
            out[f.check] = out.get(f.check, 0) + 1
        return out

    def has_error(self) -> bool:
        return any(f.severity == Severity.ERROR for f in self.flags)

    def as_frame(self):
        import pandas as pd
        return pd.DataFrame([f.as_dict() for f in self.flags])


def analyze_frames(
    ep: Episode,
    ranges: Optional[Dict[str, tuple]] = None,
    config: Optional[DetectorConfig] = None,
) -> FrameReport:
    """Run every frame-level detector with one shared operator configuration."""
    config = config or DetectorConfig(ranges=ranges or {})
    effective_ranges = dict(config.ranges)
    if ranges:
        effective_ranges.update(ranges)
    nominal_dt = 1.0 / ep.fps if ep.fps else None
    flags: List[FrameFlag] = []
    flags += check_dropped_frames(ep, nominal_dt)
    flags += check_timing_drift(
        ep,
        nominal_dt,
        jitter_tol=config.jitter_tolerance,
        cadence_tol=config.cadence_tolerance,
    )
    flags += check_stuck_channels(
        ep, allowed_static_channels=config.allowed_static_channels,
    )
    flags += check_saturation(ep)
    flags += check_out_of_range(ep, effective_ranges)
    flags += check_sensor_noise(ep)
    return FrameReport(ep.episode_index, ep.n_frames, flags)
