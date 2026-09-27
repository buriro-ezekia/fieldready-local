# FieldReady Local

A local survey-review assistant under development for the Amazon Developer Hackathon.
The intended entry is a **simulated Alexa+ experience with a real local MCP backend**;
this is not a live Alexa+ integration or an Amazon-certified application.

## Current status: first foundation, not a finished application

Implemented: deterministic CSV validation, immutable stored source snapshots, SQLite
review history, explicit CLI confirmation, replay/stale-write protection, paginated
findings, synthetic fixtures and 41 locally executed core tests.

An official MCP Python SDK v2 adapter and a real HTTP integration-check script are
included, but **MCP execution has not yet been verified**. This implementation environment
could not download dependencies. No browser UI, AI inference or full offline-product
verification is claimed. Milestone M0 remains open.

## Try the core now — no package installation or GitHub Actions required

From the repository root, using Python 3.11 or newer:

```powershell
python scripts/check_local.py
python scripts/fieldready.py demo
```

Use `py` instead of `python` where that is your configured Windows launcher.
The synthetic demo has **8 records, 6 findings affecting 6 records**, and **2 component-total
checks that cannot be evaluated** because a prerequisite is missing or invalid.
The demo prints its run ID; identifiers such as `0001` retain their leading zeros.

Local storage defaults to `.fieldready-local/fieldready.sqlite3` under your home directory,
not inside the repository. `--db PATH` overrides it. Each `demo` call creates a new run;
use the printed run ID to reopen a previous run, not a new `demo` invocation.

```powershell
python scripts/fieldready.py summary RUN_ID
python scripts/fieldready.py findings RUN_ID
python scripts/fieldready.py review FINDING_ID --status confirmed --reason "Checked against the synthetic answer key" --revision 0 --request-id my-review-001 --confirm
python scripts/fieldready.py summary RUN_ID
```

Replace `RUN_ID` and `FINDING_ID` with printed values. Without `--confirm`, the review
command refuses to save. The model-facing MCP service has **no review-write tool**.
A confirmed finding means the supervisor completed that review, not that the source
record was corrected. `open` and `follow_up` count as unresolved; `confirmed` and
`dismissed` count as reviewed.

## MCP integration: next verification gate

Use an isolated environment and the opt-in integration check:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
.\.venv\Scripts\python.exe scripts/check_local.py --integration
```

The integration check starts a real local server and SDK client, validates a registered
synthetic batch over Streamable HTTP, checks tool exposure, stops the server, confirms
a review through the trusted CLI, restarts the server and reads the saved state through
MCP. **Missing dependencies return a non-zero status, not a successful skip.**

No resolved dependency lockfile is included yet. The SDK/client versions must be
installed, tested and locked; ranges in `pyproject.toml` are not a reproducible lock.
See [setup instructions](docs/setup.md) and [verification evidence](docs/verification.md).

## Cost and privacy boundaries

No cloud compute, hosted database, external inference API or paid runner is required by
this contribution. The core uses only Python's standard library. Initial dependency
and future model downloads still need internet access. Existing hardware, electricity
and connectivity are not included in the zero-additional-service-cost target.

**No GitHub Actions workflow is added.** The maintainer reports budget-limit failures;
local test evidence remains separate from GitHub job status. Billing and repository
protection settings have not been changed.

Use only the supplied fictional questionnaire and synthetic records at this stage.
The prototype has not undergone a production privacy/security review. The MCP service
is loopback-only and requires a locally generated token; do not tunnel or expose it.
The local database is not encrypted, and its history is not tamper-proof.

## Structure and next work

- `src/fieldready/`: rules, persistence, local CLI and MCP adapter.
- `tests/`: standard-library core and request-guard tests.
- `scripts/`: source-checkout launcher and separate core/MCP checks.
- `docs/`: setup, verification, architecture and remaining M0 work.

The next gate is successful real MCP execution on a dependency-enabled machine, followed
by a minimal browser interface and measured, actual local-model explanations. The
application will not silently substitute paid APIs when a local model is unavailable.

## Licence

Apache-2.0. The repository's original `LICENSE` is preserved.
