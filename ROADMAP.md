# Roadmap

## Implemented

- LeRobot v2/v3 metadata loading
- Episode task-label, length, and task-string coverage analysis
- Bounded frame parquet loading and schema validation
- Frame sequence, timestamp, cadence, range, flatline, clipping, and noise checks
- Explainable 0–100 quality scoring and calibrated anomaly ranking
- Content-addressed clean/review/quarantine ingest routing with an audit manifest
- Bounded live frame ingestion with immediate operator feedback
- Streamlit portal for configuration, upload, replay, scoring, and dataset review
- Pinned, checksum-verified, video-free demo-data download
- Network-free automated tests and GitHub Actions validation
- Operator review queue with promote / reject / request-recollection actions
- Transport-agnostic collector adapter with disconnect, partial-episode, and
  backpressure policies
- Named per-robot profiles (FPS, channel roles, ranges, static channels, task
  family) with a persistent store
- Task-conditioned anomaly baselines with a global fallback

## Next

- Normalize task descriptions before computing semantic coverage targets
- Validate score thresholds against labeled good/recollect decisions
- Produce the final demo recording

## Deployment work required

Before public or multi-user deployment, add authentication, tenant isolation,
request limits, malware scanning, encrypted retention, and a durable transactional
audit store. See `SECURITY.md`.
