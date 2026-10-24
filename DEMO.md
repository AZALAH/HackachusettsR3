# Demo guide

A tight, repeatable path for showing DataMon in about four minutes, plus a
deterministic fallback and a backup recording command. Every claim here maps to
something the UI or a script actually shows — nothing is narrated that the code
does not do.

## One-time setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,dashboard]" -c requirements-demo.txt
python scripts\download_frames.py
streamlit run dashboard.py
```

Open <http://localhost:8501>.

## Live path (the main story, ~4 min)

1. **Frame it.** "Bad robot demonstrations poison a training run, and you only
   find out after. DataMon gates each episode while the operator can still redo
   it."
2. **Dataset quality tab.** Show DROID episode scores and the per-episode
   reasons. Point at the lowest-scoring episode — the score is explainable, not
   a black box.
3. **Label / coverage tab.** Show BridgeData's missing and gibberish task
   labels, and the singleton-task count as a coverage lead.
4. **Ingest gate tab.** Replay one episode through the stream API. Watch the
   live per-frame feedback, then the final accept / review / quarantine verdict.
5. **Review queue tab.** Take a `review` item and promote it to clean (or reject
   it, or request recollection). Open its audit history — the decision is
   appended, the content ID is preserved, nothing is silently overwritten.
6. **Robot profile (sidebar).** Save the current rig settings as a profile, then
   reapply it — one click instead of retyping FPS, ranges, and static channels.
7. **Close it.** "Upload and live-stream data pass through the same gate before
   anything reaches training."

## Deterministic injected-fault path (no UI, always identical)

Use this when you need a guaranteed, reproducible failure on screen:

```powershell
python scripts\run_gate.py          # content routing + a dropped-frame reject
python scripts\run_frame_quality.py # injected drops, drift, flatlines, noise, clipping
python scripts\run_collector.py     # live transport: clean disconnect, dropped partial, backpressure
```

`run_collector.py` is the headline for the "real collector" story: it simulates a
transport that disconnects mid-episode and that overruns its queue, and shows the
gate catching both — without any network.

These scripts inject faults into copies; they never alter the downloaded source
data.

## Backup screen recording

Record the live path once as a fallback in case live demo hardware fails. With
the dashboard running at <http://localhost:8501>:

```powershell
# Requires ffmpeg on PATH. Windows (gdigrab); adjust the region to your window.
ffmpeg -f gdigrab -framerate 15 -i title="Robot Data Quality Monitor - Streamlit" demo.mp4
```

On macOS/Linux use the OS screen recorder (QuickTime, or `ffmpeg -f avfoundation`
/ `-f x11grab`). Keep the clip under two minutes and trim to the five tabs above.

## What NOT to claim

- The anomaly value is a rank against reference episodes, not a probability that
  a demonstration is bad.
- The clean store is normalized state/action parquet, not a full LeRobot dataset
  with video.
- This is a trusted-file local prototype — see `SECURITY.md` before exposing it.
