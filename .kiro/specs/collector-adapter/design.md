# Collector adapter — design & tasks

## Design
`CollectorAdapter` wraps one `StreamIngestor`. The producer side (`submit`) and
consumer side (`drain`) are separated by a bounded `deque` under a lock, so an
acquisition thread and the gating loop can run independently.

- `Frame` dataclass: one acquired frame, transport-independent.
- `submit(frame)`: enqueue; on overflow apply the backpressure policy.
- `drain()`: push queued frames into the stream; a changed episode id finalizes
  the previous episode first.
- `disconnect()`: drain, then finalize a salvageable partial.
- `abort()`: clear the queue and discard the open episode without gating.
- Added `StreamIngestor.discard()` for a true no-gate buffer reset (the existing
  `end_episode()` always gates, which is wrong for a discard).

Keeping transport out of this module is the point: the detector and gate never
change when the transport does.

## Tasks
- [x] `datamon/collector.py`: `Frame`, `BackpressurePolicy`, `CollectorStats`,
      `CollectorAdapter` (submit/drain/disconnect/abort + policies).
- [x] `StreamIngestor.discard()`.
- [x] `scripts/run_collector.py` demo on real DROID data.
- [x] Tests for disconnect, partial salvage/discard, both backpressure modes,
      abort, episode-boundary close, callback.
- [x] Checks green; merged via PR #2.
