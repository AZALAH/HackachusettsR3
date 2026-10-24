---
inclusion: always
---

# Engineering conventions

These are the standing rules we direct Kiro to follow on DataMon. They are not
aspirational — every feature in this repo was built under them.

## Workflow
- Every feature lands on its own `feature/<name>` branch, never directly on `main`.
- Each branch opens a pull request and is merged after the checks below pass.
- `main` is protected in practice: no direct pushes, no force-pushes.

## Definition of done (run before every merge)
- `python -m ruff check .` — clean.
- `python -m pytest -W error::RuntimeWarning` — all green, with new tests for new code.
- `python -m compileall -q datamon dashboard.py scripts tests` — clean.
- For dashboard changes, a Streamlit `AppTest` run with no exceptions.
- For gate changes, `python scripts/run_gate.py` on real data with nothing leaking
  to the clean route.

## Honesty rules (these win over a nicer-sounding claim)
- Never overclaim. The anomaly value is an empirical upper-tail RANK, not a
  probability of failure. The login is DEMO-GRADE, not production SSO.
- Never fabricate evidence: no empty folders to tick a box, no fake data.
- Keep the data downloader bounded, pinned, checksum-verified, and video-free.

## Code style
- Match the existing module's style; no new dependencies without cause.
- Transport/UI concerns stay out of the detector and gate modules.
- Tests are synthetic and network-free; CI never depends on downloading data.

## Accessibility
- Any audio or motion feature ships a visible equivalent (captions, text) and
  respects reduced-motion.
