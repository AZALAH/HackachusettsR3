# Operator review loop — tasks

- [x] Add `OperatorAction` enum to `datamon/gate.py`.
- [x] Add `action`, `note`, `fps` to `AdmitResult` and its manifest record.
- [x] Populate `fps` on every `evaluate()` result.
- [x] Implement `review_queue()` (worst-score-first) and `history(ingest_id)`.
- [x] Implement `operator_decision()` with reconstruct → re-route → append-event,
      guarding unknown IDs and items not in review.
- [x] Add the "Review queue" dashboard tab (score, reasons, note, 3 actions,
      audit history).
- [x] Tests: queue, promote, reject, recollect, history preservation, guards.
- [x] Checks green: ruff, pytest, compileall, Streamlit AppTest, run_gate.py.
- [x] Merged via PR #1.
