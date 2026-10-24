# How we used Kiro

DataMon was built by directing **Kiro** (via Kiro Crew) through a spec-driven
workflow. This folder is the evidence: the steering docs that governed every
session, and the per-feature specs we worked from.

## Tools
- **Kiro Crew** — an autonomous agent layer over Kiro. We drove development
  through it in a conversational loop: state a feature, agree on a spec, let the
  agent implement + test on a branch, review, merge.

## Spec-driven development
Each feature under `specs/` has a requirements → design → tasks breakdown written
BEFORE implementation, then checked off as it landed. Working from a spec kept
each change scoped and testable, and made "done" objective (see
`steering/conventions.md`). This beat vibe-coding on a multi-feature project:
every PR mapped to a spec, and the test gate caught regressions before merge.

## Steering docs
`steering/conventions.md` and `steering/product.md` are loaded into every
session. They enforced the workflow (branch → PR → green checks → merge), the
honesty rules (anomaly = rank not probability; login = demo-grade), and the
domain vocabulary, so the agent stayed consistent across many sessions.

## Specs in this folder
| Feature | PR | Spec |
|---------|----|------|
| Operator review loop | #1 | `specs/operator-review-loop/` |
| Collector adapter | #2 | `specs/collector-adapter/` |
| Robot profiles | #3 | built under the same conventions |
| Task-conditioned anomaly baselines | #4 | built under the same conventions |
| Demo docs | #5 | built under the same conventions |
| Narrated accessible tour | #6 | `specs/accessible-tour/` |
| Grounded help agent | #7 | built under the same conventions |
| Visual theme + branding | #8 | built under the same conventions |
| Demo-grade login (2 users) | #9 | built under the same conventions |

Every feature followed the same definition of done: ruff, pytest (with new
tests), compileall, a Streamlit AppTest for UI changes, and `run_gate.py` for
gate changes.
