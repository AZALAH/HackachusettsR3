# Operator review loop — design

## Approach
Build on the existing content-addressed gate and append-only `manifest.jsonl`
rather than adding a new store. The latest manifest record per `ingest_id`
already defines an episode's current route, so a review decision is just a new
record with a changed route and an operator action.

## Changes
- `OperatorAction` enum: `AUTOMATED` (the gate's own decision) plus
  `PROMOTE` / `REJECT` / `RECOLLECT`.
- `AdmitResult` gains `action`, `note`, and `fps`; `fps` is persisted so the
  stored episode can be reconstructed at the right rate.
- `IngestGate.review_queue()` — latest records routed to review, worst-first.
- `IngestGate.history(ingest_id)` — every event for one content ID, oldest-first.
- `IngestGate.operator_decision(ingest_id, action, note)`:
  1. Validate the ID exists and is currently in review.
  2. Reconstruct the exact episode from its stored parquet.
  3. Re-evaluate to keep the original scores, then force the route from the action
     (PROMOTE→clean, REJECT→quarantine, RECOLLECT→review).
  4. Write to the new route, remove the old copy, append a new manifest event.

## UI
A "Review queue" dashboard tab: per-item score, reasons, a note field, three
action buttons, and an expandable audit history.

## Why not a separate review database
It would duplicate state already in the manifest and risk the two disagreeing.
The manifest is the single source of truth; this reuses it.
