# Testing instructions

DataMon is behind a demo-grade login. Per the hackathon rules, here are working
credentials for judging and testing.

## Run it locally

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,dashboard]" -c requirements-demo.txt
.venv\Scripts\python.exe scripts\download_frames.py
.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Open <http://localhost:8501>.

## Login credentials

| Role | Username | Password |
|------|----------|----------|
| Programmer | `programmer` | `101010` |
| Judge | `judge` | `Hello World!` |

Either account opens the full app. The roles are for demonstration; both have the
same access in this prototype.

## What to try

1. **Guided tour** — sidebar → "Start guided tour". Narrated, arrow-guided
   walkthrough of every feature.
2. **Help agent** — bottom-right "Ask about the interface". Click a question or
   type your own.
3. **Ingest gate** — replay an episode and watch the accept/review/reject verdict.
4. **Review queue** — promote, reject, or request recollection; open the audit
   history.
5. **Dataset quality** — per-episode scores, verdicts, and reasons on real
   DROID/BridgeData slices.

## Security note

This login is **demo-grade**: salted PBKDF2 password hashing, constant-time
comparison, failed-attempt lockout, and idle session timeout — but no TLS, no
real user database, and it runs as a local trusted-file app. The credentials
above are intentionally public for judging. See [SECURITY.md](SECURITY.md) for
the controls a networked deployment would require.
