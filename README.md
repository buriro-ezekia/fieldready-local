# FieldReady Local

A local survey-review assistant for the Amazon Developer Hackathon: a **simulated
Alexa+ experience with a real local MCP backend**, not a live Alexa+ integration or
an Amazon-certified application. Use synthetic data only.

## Current status — M0 remains open

Implemented: deterministic CSV checks, immutable source snapshots, SQLite review
history, explicit confirmation, stale/replay protection, paginated findings, a local
CLI and an official MCP Python SDK v2 server. The maintainer has reported a successful
Windows MCP check: protocol 2026-07-28 and persistent review state after restart.

New in this slice: an authenticated local browser interface, SDK-based web-to-MCP
client, owned-service launcher and optional local Ollama explanations. **38 new unit
tests passed with labelled stubs.** The actual new web-to-MCP path, browser rendering
on Windows, real local inference and complete offline workflow remain verification
gates. See [current evidence and browser guide](docs/browser.md).

## Run the core without package installation

From the repository root, with Python 3.11 or newer:

```powershell
python scripts/check_local.py
python scripts/fieldready.py demo
```

The synthetic example contains **8 records, 6 findings affecting 6 records**, and
**2 non-evaluable component-total checks**. IDs retain leading zeros. Each `demo`
invocation creates a new run. Use the printed run ID to reopen an existing review:

```powershell
python scripts/fieldready.py summary RUN_ID
python scripts/fieldready.py findings RUN_ID
python scripts/fieldready.py review FINDING_ID --status confirmed --reason "Checked against the synthetic answer key" --revision 0 --request-id my-review-001 --confirm
```

Local state defaults to `.fieldready-local/fieldready.sqlite3` under your home directory,
not the repository. `--db PATH` overrides it. Without explicit confirmation, no review
is saved. Confirmed means reviewed, not corrected. Open/follow-up remain unresolved.

## Install the optional MCP dependencies and verify

Use your existing virtual environment, or create one with `python -m venv .venv` first:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_local.py --integration
.\.venv\Scripts\python.exe scripts/check_web.py
```

Stop on an error. Missing dependencies return a non-zero status, never a successful
skip. Both integration checks use temporary databases. The web check exercises real
HTTP -> MCP -> SQLite and restart persistence; it does not render a browser or run AI.

## Open the local browser workspace

```powershell
.\.venv\Scripts\python.exe scripts/run_web.py
```

Open the full local session link printed in the terminal and keep its token private.
Create a synthetic review, inspect a finding, enter a reason, explicitly confirm a
decision and reopen the saved review. Press Ctrl+C normally to stop owned services.
Validation/evidence use real MCP; human-approved writes use the trusted control surface.

AI is disabled by default. The review interface does not need a model. An optional
`--model "YOUR_INSTALLED_MODEL:TAG"` starts a separate local-only Ollama server.
The application never downloads a model or substitutes a paid API. See the
[browser/model guide](docs/browser.md) before enabling it.

## Cost, privacy and licence

No GitHub Actions workflow is added or dispatched. Budget-blocked jobs are not treated
as test passes or code failures; no billing/protection setting is changed. Runtime
uses your existing computer and SQLite, excluding electricity and connectivity costs.
No hosted database, cloud compute or paid inference service is required.

Do not tunnel/expose these services or commit real records, databases, model weights,
credentials or raw logs. The local database is not encrypted or tamper-proof. The
prototype has not had a production security/privacy audit. Package ranges are not a
resolved lockfile; dependency locking and packaging verification remain pending.

Apache-2.0: the original `LICENSE` is preserved. Earlier foundation evidence is in
[docs/verification.md](docs/verification.md); current additions and limitations are in
[docs/browser.md](docs/browser.md).
