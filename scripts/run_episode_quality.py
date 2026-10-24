"""Analyze BridgeData V2 episode labels, lengths, and task-string coverage."""

from __future__ import annotations

from datamon.episode_quality import analyze_episodes
from datamon.lerobot import load_episodes, load_info


def main() -> None:
    try:
        info = load_info()
        episodes = load_episodes()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(
            f"Demo metadata is unavailable ({error}). "
            "Run: python scripts/download_frames.py"
        ) from error

    print(
        f"Dataset: {info.robot_type}; {info.total_episodes:,} episodes; "
        f"{info.total_frames:,} frames @ {info.fps:g} fps"
    )
    report = analyze_episodes(episodes)
    print("Flags by severity:", report.counts_by_severity())
    print("Flags by check:   ", report.counts_by_check())
    print(f"Episodes with warning/error: {report.flagged_episode_fraction() * 100:.1f}%")
    coverage = report.coverage
    print(f"Unique task strings:       {coverage['unique_tasks']:,}")
    print(f"Missing-label rate:        {coverage['missing_label_rate'] * 100:.1f}%")
    print(f"Singleton task strings:    {coverage['singleton_tasks']:,}")
    print(f"Median episode length:     {coverage['median_episode_length']:.0f} frames")
    print("\nExample flag of each type")
    seen = set()
    for flag in report.flags:
        if flag.check not in seen:
            seen.add(flag.check)
            print(
                f"  [{flag.severity.value:5s}] episode {flag.episode_index:>6} "
                f"{flag.check}: {flag.reason}"
            )


if __name__ == "__main__":
    main()
