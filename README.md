# DataMon

[![CI](https://github.com/jesseUML/HackachusettsR3/actions/workflows/ci.yml/badge.svg)](https://github.com/jesseUML/HackachusettsR3/actions/workflows/ci.yml)

DataMon is a pre-training quality gate for robot demonstration data, built for
Hackachusetts 2026 R3. It catches collection defects while an operator can still
redo the episode instead of discovering them after a training run.

Continuing development? Start with [HANDOFF.md](HANDOFF.md) for the architecture,
validated commands, data safeguards, known limits, and prioritized next work.
Presenting it? [DEMO.md](DEMO.md) has a four-minute scripted path and a
deterministic fault fallback.

## What it checks

- Missing, vague, or likely-gibberish task descriptions
- Missing, duplicate, backward, and late frames
- Wrong capture cadence, timestamp jitter, and timing drift
- Non-finite or operator-configured out-of-range state/action values
- Flatlined channels, likely clipping, and channel-relative noise
- Unusual episode duration, motion, smoothness, and action effort
- Task-string concentration and underrepresented labels as coverage leads

Every episode receives an explainable 0–100 score. The ingest gate then routes
the exact evaluated episode to one of three local staging areas:

```text
incoming episode -> checks + score -> clean / review / quarantine
```

Hard integrity failures and invalid labels are quarantined regardless of score.
Content-addressed filenames prevent two sources or repeated episode numbers from
overwriting each other. The clean output is normalized state/action parquet for
staging; it is not a complete LeRobot dataset and does not include image/video
assets.

## Dashboard

The Streamlit portal provides:

- A guarded parquet upload flow with task-description entry
- Replay through the same frame-by-frame stream API used by live collectors
- Immediate frame-order, timing, and non-finite-value feedback
- Per-episode scores, reasons, state traces, and accept/review/reject decisions
- An operator **review queue**: promote a held episode to clean, reject it, or
  request recollection, with every decision appended to the audit trail
- Dataset-level quality and BridgeData V2 label/coverage summaries
- Saved **robot profiles**: capture a rig's FPS, channel ranges, and static
  channels once, then reapply them in one click
- Configurable FPS, timing tolerance, score bands, channel bounds, and expected
  static channels

The dashboard is a trusted-file local prototype. Read [SECURITY.md](SECURITY.md)
before exposing it on a network.

## Quick start

Python 3.9–3.13 is supported.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,dashboard]"
# For the exact release-tested versions, append: -c requirements-demo.txt
python scripts\download_frames.py
streamlit run dashboard.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,dashboard]'
python scripts/download_frames.py
streamlit run dashboard.py
```

Open <http://localhost:8501>. All commands assume the repository root as the
working directory. `requirements-demo.txt` pins the exact direct dependency
versions used for this release; pass it with `-c requirements-demo.txt` when you
need a reproducible demo environment.

`scripts/download_frames.py` downloads exactly 10 pinned, checksum-verified
files totaling 7.23 MB. It downloads no videos and enforces both per-file and
total byte limits. Downloaded and ingested data stays under ignored `data/`
paths and is not committed.

## Command-line demonstrations

```bash
python scripts/run_episode_quality.py  # 53k BridgeData metadata records
python scripts/run_frame_quality.py    # real episodes plus injected defects
python scripts/run_scoring.py          # DROID-100 scores and anomaly ranking
python scripts/run_gate.py             # content routing and stream feedback
python scripts/run_collector.py        # simulated live transport + policies
```

Each command reports a clear prerequisite message if the bounded dataset slice
has not been downloaded.

## Library example

```python
from pathlib import Path

from datamon.frames import load_episode_file
from datamon.gate import GateConfig, IngestGate
from datamon.stream import StreamIngestor

reference = load_episode_file(Path("reference.parquet"), fps=15, source="robot-a")
gate = IngestGate(Path("data/ingest_live"), GateConfig()).calibrate([reference])
stream = StreamIngestor(gate, fps=15)

for frame_index, (timestamp, state, action) in enumerate(robot_frames):
    feedback = stream.push_frame(
        episode_index=42,
        frame_index=frame_index,
        timestamp=timestamp,
        state=state,
        action=action,
        task="place the marker in the pot",
        source="robot-a",
    )
    if not feedback.ok:
        notify_operator(feedback.warnings)

result = stream.end_episode()
print(result.decision, result.reasons)
```

## Project layout

```text
datamon/
  frames.py           bounded parquet loading and Episode validation
  lerobot.py          LeRobot v2/v3 metadata loading
  episode_quality.py  task-label, length, and coverage checks
  frame_quality.py    frame, timing, state, and action checks
  scoring.py          explainable score and calibrated anomaly rank
  gate.py             content-addressed routing and audit manifest
  stream.py           bounded live episode buffering and feedback
  collector.py        transport-agnostic adapter (disconnect/partial/backpressure)
  profiles.py         named per-robot profiles and persistent store
  monitor.py          cached dataset orchestration
dashboard.py          Streamlit operator portal
scripts/              verified data downloader and demonstrations
tests/                synthetic, network-free regression tests
```

## Data and validation

The demo uses a bounded subset of BridgeData V2 and DROID-100. Sources,
revisions, licenses, and integrity details are in [DATASETS.md](DATASETS.md).
Third-party data is never redistributed by this repository.

Run the release checks with:

```bash
python -m ruff check .
python -m pytest
python -m compileall -q datamon dashboard.py scripts tests
```

GitHub Actions runs the same checks on Python 3.9 and 3.13.

## Limitations

- Detector thresholds are prototype defaults. Calibrate them per robot with a
  saved profile (FPS, channel ranges, static channels, task family) before
  trusting warnings on an unfamiliar rig.
- The anomaly value is an empirical upper-tail rank against reference episodes,
  not a probability that a demonstration is bad. Baselines can be conditioned
  per task so an episode is judged against other demonstrations of the same task.
- Coverage metrics operate on raw task strings; semantic label normalization is
  required before using them to drive collection budgets.
- `scripts/run_collector.py` simulates a live transport through `CollectorAdapter`;
  a real deployment supplies the transport (ROS 2, WebSocket, SDK) that calls
  `adapter.submit(...)`. The adapter owns disconnect, partial-episode, and
  backpressure policy, but the network client itself is deployment-specific.
- No quality gate can prove that accepted data will train a successful model.

## License

Original source code and documentation are released under the [MIT License](LICENSE).
Downloaded datasets retain their upstream licenses.
