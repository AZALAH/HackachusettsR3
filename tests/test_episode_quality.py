"""Tests for episode-level data quality checks."""

import pandas as pd

from datamon.episode_quality import (
    Severity,
    _looks_like_gibberish,
    analyze_episodes,
    check_label_quality,
    check_length,
)


def _df(rows):
    out = []
    for i, (task, length) in enumerate(rows):
        out.append({
            "episode_index": i,
            "length": length,
            "n_tasks": 1 if task else 0,
            "task": task,
            "tasks": [task] if task else [],
        })
    return pd.DataFrame(out)


def test_gibberish_detection():
    assert _looks_like_gibberish("bmbfbbfgjjg")
    assert _looks_like_gibberish("xkcdzzptrn")
    assert not _looks_like_gibberish("open the drawer")
    assert not _looks_like_gibberish("put broccoli in pot")
    assert not _looks_like_gibberish("close")  # short real word, not flagged


def test_missing_label_flagged_as_error():
    df = _df([("", 40), ("open drawer", 40)])
    flags = check_label_quality(df)
    missing = [f for f in flags if f.check == "missing_label"]
    assert len(missing) == 1
    assert missing[0].episode_index == 0
    assert missing[0].severity == Severity.ERROR


def test_vague_label_flagged_as_warn():
    df = _df([("end effector reaching pot or pan", 40)])
    flags = check_label_quality(df)
    assert any(f.check == "vague_label" and f.severity == Severity.WARN for f in flags)


def test_garbage_label_flagged():
    df = _df([("bmbfbbfgjjg", 40)])
    flags = check_label_quality(df)
    assert any(f.check == "garbage_label" for f in flags)


def test_degenerate_and_outlier_length():
    rows = [("task", 35)] * 20 + [("short", 2), ("long", 300)]
    df = _df(rows)
    flags = check_length(df)
    assert any(f.check == "degenerate_length" for f in flags)
    assert any(f.check == "length_outlier" for f in flags)


def test_analyze_produces_coverage():
    df = _df([("a", 35), ("a", 36), ("", 35), ("b", 34)])
    report = analyze_episodes(df)
    assert report.n_episodes == 4
    assert 0.0 <= report.coverage["missing_label_rate"] <= 1.0
    assert report.coverage["unique_tasks"] == 2  # 'a' and 'b'


def test_null_label_is_treated_as_missing():
    frame = pd.DataFrame([{
        "episode_index": 8,
        "length": 20,
        "n_tasks": 0,
        "task": None,
        "tasks": [],
    }])
    flags = check_label_quality(frame)
    assert any(flag.check == "missing_label" for flag in flags)


def test_test_tube_label_is_not_treated_as_placeholder():
    frame = _df([("test tube into rack", 20)])
    flags = check_label_quality(frame)
    assert not any(flag.check == "vague_label" for flag in flags)
