# Security and data-handling scope

This project is a local hackathon prototype for trusted robot-data files. It is
not a hardened multi-user upload service.

- Keep the Streamlit server bound to a trusted machine/network.
- Do not upload secrets, personal data, or untrusted files.
- Uploads are limited to 50 MB and validated as bounded LeRobot parquet.
- Processed episodes and audit records are written beneath `data/ingest_live/`.
  That directory is ignored by Git but is not encrypted.
- Delete `data/ingest_live/` when its retained records are no longer needed.
- Before any public deployment, add authentication, tenant isolation, malware
  scanning, retention controls, process isolation, and request-rate limits.

Report repository security issues through the GitHub repository's issue tracker
without including sensitive data.
