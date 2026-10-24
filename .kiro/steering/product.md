---
inclusion: always
---

# DataMon product context

DataMon is a pre-training quality gate for robot demonstration data
(Hackachusetts R3, Robotics & Hardware track). It scores each LeRobot-style
episode, explains the score, and routes the exact evaluated episode to clean,
review, or quarantine — so bad data is caught while an operator can still redo
the recording, not after a wasted training run.

## Domain facts Kiro must keep straight
- Datasets are real public robot datasets: DROID-100 and BridgeData V2, used as
  bounded, checksum-verified slices.
- "state" is proprioception; "action" is the commanded signal. Channels are
  generic (`state_0`, ...) unless a robot profile names their roles.
- Hard integrity failures (dropped frames, non-finite values, missing/garbage
  labels, < 5 frames) quarantine regardless of score.
- Persistence is content-addressed; re-evaluating identical content re-routes it
  rather than duplicating it. The audit manifest is append-only.

## Vocabulary
- accept / review / quarantine — the three routes.
- promote / reject / recollect — the operator's review-queue actions.
- rank, not probability — how the anomaly score must always be described.
