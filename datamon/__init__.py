"""datamon — live robot data-collection quality monitor (Hackachusetts R3).

Watches robot demonstration data (LeRobot format) and flags quality problems
that otherwise get caught too late:
  * poor / missing / garbage demonstration labels
  * length and coverage anomalies across episodes
  * (frame layer) dropped frames, timing drift, sensor noise, stuck channels

Headline dataset: BridgeData V2 (IPEC-COMMUNITY/bridge_orig_lerobot).
"""

__version__ = "0.1.0"
