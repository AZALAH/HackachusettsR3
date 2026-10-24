# Collector adapter — requirements

## Problem
Replay demonstrates the stream API but is not a real transport. A live
deployment pulls frames from ROS 2, a WebSocket, or an SDK callback, and those
transports force three concerns a file loader never sees: disconnect,
partial episodes, and backpressure. None of that may leak into the detector or
gate.

## User stories
1. As an integrator, I connect my transport by calling one method,
   `adapter.submit(Frame(...))`, from my acquisition callback — nothing else.
2. As an operator, a clean disconnect gates the open episode; a crash discards it.
3. As an operator, a transport that stalls or floods never corrupts stored data.

## Acceptance criteria
- `datamon/collector.py` imports no transport library.
- Disconnect policy: `disconnect()` flushes a salvageable partial; `abort()`
  discards. A partial shorter than `min_frames_on_disconnect` is discarded.
- Backpressure policy: a bounded queue, either `DROP_OLDEST` (counts drops so the
  gate's dropped-frame check still fires on the index gap) or `BLOCK_PRODUCER`.
- Thread-safe submission; one episode buffered at a time.
- A new episode id closes the previous episode.
- `scripts/run_collector.py` demonstrates all three policies on real data.
- Synthetic, network-free tests cover every policy.
