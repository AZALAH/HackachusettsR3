"""Episode-level data quality checks for robot demonstration datasets.

Maps R3's named problems ("poor demonstrations, gaps in coverage") to concrete,
explainable checks on the episode metadata. Each check produces Flags with a
severity and a human reason, so the operator dashboard can say WHAT is wrong and
WHY — real-time feedback, not just a score.

Checks (metadata-only, no frame data needed):
  * missing_label       — empty task description
  * garbage_label       — non-word gibberish (e.g. "bmbfbbfgjjg")
  * vague_label         — placeholder/non-task text (e.g. "end effector reaching ...")
  * duplicate_label     — many episodes share one label (coverage skew)
  * length_outlier      — episode much longer/shorter than typical (robust z-score)
  * degenerate_length   — too few frames to be a usable demonstration

Plus a dataset-level coverage report: task distribution, label-missing rate,
and under-represented tasks (gaps in coverage).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class Flag:
    episode_index: int
    check: str
    severity: Severity
    reason: str

    def as_dict(self) -> dict:
        return {
            "episode_index": self.episode_index,
            "check": self.check,
            "severity": self.severity.value,
            "reason": self.reason,
        }


# --- individual checks -----------------------------------------------------

_WORD_RE = re.compile(r"[a-z]+")
_VAGUE_PATTERNS = [
    "end effector reaching",
    "end effector",
    "move the arm",
    "do something",
    "n/a",
    "none",
    "test",
]


def _looks_like_gibberish(text: str) -> bool:
    """Heuristic: a single long run of letters with no spaces and poor
    vowel structure (e.g. 'bmbfbbfgjjg')."""
    t = text.strip().lower()
    if not t or " " in t:
        return False
    if len(t) < 5:
        return False
    letters = _WORD_RE.findall(t)
    if not letters:
        return False
    joined = "".join(letters)
    if len(joined) < len(t) * 0.8:
        return False  # has digits/symbols, treat separately
    vowels = sum(c in "aeiou" for c in joined)
    vowel_ratio = vowels / len(joined)
    # real words have ~35-45% vowels; gibberish keyboard-mashing is far lower
    return vowel_ratio < 0.2


def _normalize_task(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()


def check_label_quality(df: pd.DataFrame) -> List[Flag]:
    flags: List[Flag] = []
    for _, row in df.iterrows():
        ep = int(row["episode_index"])
        task = _normalize_task(row.get("task"))
        low = task.lower()
        if not task:
            flags.append(Flag(ep, "missing_label", Severity.ERROR,
                              "episode has no task description"))
            continue
        if _looks_like_gibberish(task):
            flags.append(Flag(ep, "garbage_label", Severity.ERROR,
                              f"task label looks like gibberish: {task!r}"))
            continue
        if any(
            low == pattern or (" " in pattern and low.startswith(f"{pattern} "))
            for pattern in _VAGUE_PATTERNS
        ):
            flags.append(Flag(ep, "vague_label", Severity.WARN,
                              f"task label is vague/placeholder: {task!r}"))
    return flags


def check_duplicate_labels(df: pd.DataFrame, min_fraction: float = 0.02) -> List[Flag]:
    """Surface task-distribution concentration as an informational signal."""
    tasks = df["task"].map(_normalize_task)
    labeled = df.loc[tasks != ""].copy()
    labeled["task"] = tasks[tasks != ""]
    if labeled.empty:
        return []
    counts = labeled["task"].value_counts()
    n = len(labeled)
    flags: List[Flag] = []
    for task, count in counts.items():
        if count / n >= min_fraction and count > 1:
            ep = int(labeled[labeled["task"] == task]["episode_index"].iloc[0])
            flags.append(Flag(
                ep, "coverage_skew", Severity.INFO,
                f"task {task!r} appears {count} times ({count / n * 100:.1f}% of labeled)",
            ))
    return flags


def check_length(df: pd.DataFrame, min_frames: int = 5, z_thresh: float = 3.5) -> List[Flag]:
    numeric = pd.to_numeric(df["length"], errors="coerce")
    lengths = numeric.to_numpy(dtype=float)
    finite = lengths[np.isfinite(lengths)]
    med = float(np.median(finite)) if finite.size else 0.0
    mad = float(np.median(np.abs(finite - med))) if finite.size else 1.0
    mad = mad or 1.0
    flags: List[Flag] = []
    for position, (_, row) in enumerate(df.iterrows()):
        ep = int(row["episode_index"])
        length = lengths[position]
        if not np.isfinite(length):
            flags.append(Flag(ep, "degenerate_length", Severity.ERROR,
                              "episode length missing or invalid"))
            continue
        if length < min_frames:
            flags.append(Flag(
                ep, "degenerate_length", Severity.ERROR,
                f"only {int(length)} frames (< {min_frames}) — too short to be usable",
            ))
            continue
        z = 0.6745 * (length - med) / mad
        if abs(z) >= z_thresh:
            flags.append(Flag(
                ep, "length_outlier", Severity.WARN,
                f"{int(length)} frames vs median {med:.0f} (robust z={z:.1f})",
            ))
    return flags


# --- orchestration ---------------------------------------------------------

@dataclass
class QualityReport:
    n_episodes: int
    flags: List[Flag]
    coverage: dict = field(default_factory=dict)

    def flags_frame(self) -> pd.DataFrame:
        return pd.DataFrame([f.as_dict() for f in self.flags])

    def counts_by_check(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for f in self.flags:
            out[f.check] = out.get(f.check, 0) + 1
        return out

    def counts_by_severity(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for f in self.flags:
            out[f.severity.value] = out.get(f.severity.value, 0) + 1
        return out

    def flagged_episode_fraction(self) -> float:
        eps = {f.episode_index for f in self.flags
               if f.severity in (Severity.WARN, Severity.ERROR)}
        return len(eps) / self.n_episodes if self.n_episodes else 0.0


def coverage_report(df: pd.DataFrame, rare_count: int = 1) -> dict:
    tasks = df["task"].map(_normalize_task)
    counts = tasks[tasks != ""].value_counts()
    return {
        "unique_tasks": int(counts.shape[0]),
        "missing_label_rate": float((tasks == "").mean()),
        "singleton_tasks": int((counts <= rare_count).sum()),
        "top_tasks": counts.head(10).to_dict(),
        "mean_episode_length": float(pd.to_numeric(df["length"], errors="coerce").mean()),
        "median_episode_length": float(pd.to_numeric(df["length"], errors="coerce").median()),
    }


def flags_for_episode(episode_index: int, task: Optional[str]) -> List[Flag]:
    """Run metadata checks available at ingest time for one episode."""
    frame = pd.DataFrame([{
        "episode_index": episode_index,
        "task": task,
    }])
    return check_label_quality(frame)


def analyze_episodes(df: pd.DataFrame) -> QualityReport:
    flags: List[Flag] = []
    flags += check_label_quality(df)
    flags += check_duplicate_labels(df)
    flags += check_length(df)
    return QualityReport(
        n_episodes=len(df),
        flags=flags,
        coverage=coverage_report(df),
    )
