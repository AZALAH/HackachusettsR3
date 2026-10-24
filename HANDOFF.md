# Teammate handoff

## What this project is

DataMon is a Hackachusetts R3 prototype that checks robot demonstrations before
they reach model training. It accepts LeRobot-style state/action frame parquet,
checks metadata and stream integrity, assigns an explainable quality score, and
routes the exact evaluated episode to:

- `clean/` — accepted for downstream staging
- `review/` — requires an operator decision
- `quarantine/` — rejected and kept away from training

The current baseline was pushed to `main` from commit `cb4cabf`. GitHub Actions
runs lint, tests, and compilation on Python 3.9 and 3.13.

## Five-minute setup

Run from the repository root.

```powershell
git clone https://github.com/jesseUML/HackachusettsR3.git
Set-Location HackachusettsR3
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,dashboard]" -c requirements-demo.txt
python scripts\download_frames.py
streamlit run dashboard.py
```

Open <http://localhost:8501>.

The downloader is deliberately bounded. It fetches 10 pinned, SHA-256-verified
files totaling 7.23 MB and no videos. Do **not** replace it with a whole-dataset
clone: the upstream robot datasets can be hundreds of gigabytes or terabytes.

## Current architecture

```text
LeRobot metadata -----------------------> episode_quality.py
                                                    |
frame parquet -> frames.py -> frame_quality.py      |
                         \                           v
                          +-----> scoring.py -> monitor.py
                                               |
upload or collector -> stream.py ------------> gate.py
                                               |
                                      clean / review / quarantine
                                               |
                                         manifest.jsonl
```

### Main files

- `dashboard.py` — Streamlit portal, configuration, upload, replay, and reports
- `datamon/frames.py` — bounded parquet loader and `Episode` validation
- `datamon/lerobot.py` — LeRobot v2 JSONL and v3 parquet metadata loaders
- `datamon/episode_quality.py` — label, length, and coverage checks
- `datamon/frame_quality.py` — index, timing, range, flatline, clipping, noise
- `datamon/scoring.py` — rule score and calibrated IsolationForest rank
- `datamon/gate.py` — policy, content-addressed routing, and audit manifest
- `datamon/stream.py` — bounded single-episode live ingestion API
- `datamon/monitor.py` — cached orchestration for datasets and the dashboard
- `scripts/download_frames.py` — immutable, checksummed demo-data manifest
- `DATASETS.md` — dataset revisions, licenses, and provenance
- `SECURITY.md` — local-demo security and retention boundaries
- `ROADMAP.md` — remaining product work

## Gate policy

Default score bands:

- `80–100`: accept
- `55–79.99`: review
- `<55`: reject

The thresholds are configurable, but `reject_below` must not exceed `accept_at`.
The following error checks hard-reject regardless of score:

- `dropped_frames`
- `out_of_range` (includes invalid timestamps and NaN/Inf state/action values)
- `missing_label`
- `garbage_label`

Episodes shorter than five frames are also rejected. The gate defaults to
`require_task=True`, so a collector or upload must supply a meaningful task
string. DROID and Bridge sample tasks are joined from their metadata files.

Persistence is content-addressed by source, metadata, and array bytes. The gate
always reconstructs and stores the exact `Episode` it evaluated; it never copies
an entire multi-episode upload into the clean area. Reprocessing identical
content updates its current route instead of producing conflicting clean and
quarantine copies.

## What has been validated

At handoff time:

```text
python -m ruff check .                              passed
python -m pytest -W error::RuntimeWarning           54 passed
python -m compileall -q datamon dashboard.py scripts tests
Streamlit AppTest dashboard execution               no exceptions
python scripts/download_frames.py                   all checksums verified
python scripts/run_gate.py                          real DROID integration passed
```

Tests are synthetic and network-free. Do not make CI depend on downloading data.
Use the runner scripts for optional real-data integration checks.

## Demo path

1. Run `python scripts/download_frames.py` once.
2. Start `streamlit run dashboard.py`.
3. In **Dataset quality**, show DROID episode scores and reasons.
4. In **Label / coverage**, show missing/gibberish BridgeData task labels.
5. In **Ingest gate**, replay an episode through `StreamIngestor`.
6. Explain that upload and stream data pass through the same gate before training.
7. For a deterministic fault demonstration, run:

   ```powershell
   python scripts\run_gate.py
   python scripts\run_frame_quality.py
   ```

   The scripts inject dropped frames, timing drift, flatlines, noise, clipping,
   and non-finite values without altering the source dataset.

## Important boundaries and gotchas

- `data/` is ignored. Never force-add downloaded, uploaded, clean, review, or
  quarantined files.
- `FaultSense-Project-Notes.pdf` is a retired local file and is intentionally
  ignored; it is unrelated to the current R3 project.
- The dashboard is a trusted-file local prototype. It is not safe to expose as a
  public upload service without the controls listed in `SECURITY.md`.
- Uploads are capped at 50 MB; parquet reads are capped at 1,000,000 rows.
- `StreamIngestor` buffers one episode only. It rejects mixed episode IDs,
  changing vector widths, invalid FPS, and overlong streams.
- A live collector must pass `task` and a stable `source` value on the first
  frame. Use `StreamIngestor.push_frame(...)` from the acquisition callback.
- The clean store contains normalized state/action parquet. It is not a complete
  LeRobot dataset and does not preserve image/video assets or every optional
  upstream column.
- The anomaly score is an empirical upper-tail rank against clean reference
  episodes, not a probability of failure.
- Coverage currently counts raw task strings. Similar wording can appear as
  separate tasks; normalize or embed labels before using coverage for budgets.
- Generic channel heuristics cannot know every robot's gripper or unused DOFs.
  Configure bounds and allowed-static channels in the portal for the target rig.

## Highest-priority next work

### 1. Finish the operator review loop

Add a dashboard queue where an operator can promote a `review` item to `clean`,
reject it, or request recollection. Preserve the decision as a new audit event.
Do not move files without retaining the content ID and prior history.

### 2. Add a real collector adapter

Connect a ROS 2 subscription, WebSocket endpoint, or robot SDK callback to
`StreamIngestor.push_frame`. Keep transport concerns outside the detector and
gate modules. Add disconnect, partial-episode, and backpressure policies.

### 3. Create robot-specific profiles

Persist named profiles containing expected FPS, channel names/roles, physical
ranges, allowed-static channels, and task family. Generic `state_0` names are
fine for the demo but weak for real operator feedback.

### 4. Improve demonstration-quality modeling

Train anomaly baselines per task or task family using operator-approved episodes.
Validate score thresholds against labeled good/recollect decisions. Avoid calling
an anomaly rank an accuracy or probability.

### 5. Polish and record the demo

Prepare one short scripted path, one deterministic injected-fault path, and a
backup screen recording. Keep claims tied to what the UI and scripts actually
show.

## Development checklist

Before pushing:

```powershell
python -m ruff check .
python -m pytest -W error::RuntimeWarning
python -m compileall -q datamon dashboard.py scripts tests
```

For changes to downloads, also run `python scripts\download_frames.py` and
confirm the total remains small, pinned, and video-free. For gate changes, run
`python scripts\run_gate.py` and verify rejected content never appears under the
clean route.
