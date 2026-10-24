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

## Next

- Add a real transport adapter (ROS 2, WebSocket, or collector callback)
- Add operator promotion/rejection actions for the review queue
- Normalize task descriptions before computing semantic coverage targets
- Calibrate channel roles, ranges, and detector thresholds per robot
- Add task-conditioned anomaly baselines
- Produce the final demo recording

## Deployment work required

Before public or multi-user deployment, add authentication, tenant isolation,
request limits, malware scanning, encrypted retention, and a durable transactional
audit store. See `SECURITY.md`.
