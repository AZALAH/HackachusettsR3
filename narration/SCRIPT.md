# Narration script

One line per tutorial step, written for a confident, warm UK narrator voice and
tuned to the Hackachusetts judging criteria (real-world value, unique datasets,
Kiro usage), with a light touch of dry humor. Keep each delivery short.

## How to use this file

1. Copy each **Text** block into your voice site.
2. Export the result as an MP3.
3. Save it under `narration/audio/` using the step's **ID** as the filename,
   e.g. `step_01_welcome.mp3`.

The guided tour loads the audio for each step and shows the same text on screen
as a caption, so the tour still works for anyone who cannot hear the audio. A
missing file just plays silently.

Keep the IDs and order below unchanged — the tour matches steps to files by ID.

---

### step_01_welcome
**Text:**
Welcome to DataMon. A robot only learns from what you feed it, and one bad
demonstration can quietly teach it the wrong move. DataMon catches the bad data
before training does. I'll show you how, in a minute flat.

### step_02_sidebar_setup
**Text:**
We start on the left. This panel sets your data source and how strict the checks
are — the rules of the road, before a single recording rolls in.

### step_03_robot_profile
**Text:**
Every robot is different. Save one as a profile — its speed, its limits, its
quirks — and load it back in a single click. Because no two robot arms have the
same idea of "normal."

### step_04_quality_bands
**Text:**
These are the pass marks. Below the first line, rejected. Above the second,
accepted. In between, a human takes a look — because some calls a machine
shouldn't make alone.

### step_05_ingest_gate
**Text:**
This is the gate, the heart of it. Every recording is scored and sorted here:
clean, held for review, or quarantined — before it can ever poison a training run.

### step_06_upload_and_stream
**Text:**
Upload a finished recording, or replay a live one frame by frame. Same checks
either way. The gate doesn't care how the data arrived — only whether it's any
good.

### step_07_review_queue
**Text:**
When DataMon isn't sure, it doesn't guess — it asks you. Promote a good recording,
reject a bad one, or send it back to be recorded again. A human in the loop, by
design.

### step_08_audit_history
**Text:**
And every decision is written down — who chose what, and when. Nothing is ever
quietly overwritten. If a regulator ever asks "why did this data get through?",
you have the receipt.

### step_09_dataset_quality
**Text:**
Here's the full report card, built on real public robot datasets — DROID and
BridgeData. One row per recording, each with a score, a verdict, and the reasons
behind it. No black boxes.

### step_10_labels_coverage
**Text:**
Last, the labels. This flags recordings the robot was never properly told the
point of — the digital equivalent of "do the thing," and hoping it works out.

### step_11_closing
**Text:**
That's DataMon: good data in, bad data out, caught early. Built with Kiro —
specs, agent hooks, and property-based tests doing the heavy lifting. Teaching
robots is hard enough without teaching them bad habits.

---

## Error alert

The in-app error cue ships as a short generated tone (`alert_error.wav`, see
`scripts/make_alert_sound.py`). If you prefer a spoken cue, record this line as
`alert_error.mp3` and it overrides the tone automatically.

### alert_error
**Text:**
Heads up — that recording just failed a check. Best take a look before you carry
on.
