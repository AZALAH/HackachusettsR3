# Dataset provenance

The repository does **not** redistribute either dataset. `data/` is ignored by
Git. `scripts/download_frames.py` downloads a bounded, video-free subset from
immutable upstream revisions and verifies every file by size and SHA-256.

## BridgeData V2, LeRobot conversion

- Source: [IPEC-COMMUNITY/bridge_orig_lerobot](https://huggingface.co/datasets/IPEC-COMMUNITY/bridge_orig_lerobot)
- Upstream revision: `0e9d76d07e9df3ea3eba257b2520d4913833fad2`
- License reported by the dataset card: Apache-2.0
- Local subset: `meta/info.json`, `meta/episodes.jsonl`, and episodes 0, 4, 11,
  15, and 395 as frame parquet. No videos are downloaded.

BridgeData V2 originates from the BridgeData robot-learning dataset. Consult the
upstream dataset card and linked project for authorship and academic citation
requirements before publishing results.

## DROID-100, LeRobot conversion

- Source: [lerobot/droid_100](https://huggingface.co/datasets/lerobot/droid_100)
- Upstream revision: `87301a2d2e99340e2010c9ef0f1d8e780b08aaf9`
- License reported by the dataset card: MIT
- Local subset: one 100-episode frame parquet plus `info.json` and the matching
  episode-metadata parquet. No videos are downloaded.

DROID-100 is a small converted subset of the DROID robot-manipulation dataset.
Consult the upstream dataset card and DROID project for authorship and academic
citation requirements before publishing results.

## Retrieval and integrity

The revisions and checksums were verified on October 24, 2026. The exact file
manifest is defined in `scripts/download_frames.py`; that script is the source
of truth for byte limits, destination paths, expected sizes, and SHA-256 values.

Dataset licenses apply to downloaded data. The repository's MIT license applies
only to this project's original source code and documentation.
