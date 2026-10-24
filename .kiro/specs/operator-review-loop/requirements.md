# Operator review loop — requirements

## Problem
The gate sorts episodes into clean, review, and quarantine, but "review" was a
dead end: nothing let an operator act on a held episode. We need a human-in-the-
loop decision step that preserves the audit trail.

## User stories
1. As an operator, I can see every episode currently held for review, worst score
   first, with its reasons — so I can triage the most doubtful first.
2. As an operator, I can PROMOTE a held episode to clean, REJECT it to
   quarantine, or REQUEST RECOLLECTION (keep it in review, flagged), so the right
   thing happens to borderline data.
3. As an auditor, I can see the full history of a content ID — who decided what,
   when, and why — and know it was never silently overwritten.

## Acceptance criteria
- A decision re-routes the EXACT stored episode (reconstructed from its content-
  addressed parquet); the content ID is preserved.
- Each decision APPENDS a new manifest event; prior history is never rewritten.
- Acting on an unknown ID, or on an item not currently in review, is refused.
- `stats()` and the queue stay correct because the latest event per content ID
  wins.
- Fully covered by synthetic, network-free tests.
