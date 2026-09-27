# FieldReady Local

A local survey-review assistant for the Amazon Developer Hackathon: a **simulated
Alexa+ experience with a real local MCP backend**, not a live Alexa+ integration or
an Amazon-certified application. Use synthetic data only.

## Current status — core and automated offline workflow verified

The maintainer has demonstrated the core workflow on Windows:

**browser -> real MCP evidence -> local AI intent classification -> deterministic grounded
explanation -> human-controlled review decision**

The current synthetic prototype includes deterministic CSV checks, immutable source snapshots,
SQLite review history, explicit confirmation, stale/replay protection, paginated findings,
a local CLI, an official MCP Python SDK v2 server and an authenticated local browser interface.

Verified Windows evidence includes:

- real MCP protocol **2026-07-28**;
- **8 records, 6 findings affecting 6 records** in the bundled synthetic batch;
- review persistence across MCP/web restart;
- real web -> MCP -> SQLite integration;
- successful browser review and saved human decisions;
- real local `qwen2.5:1.5b` inference;
- a demonstrated grounded `component_total` explanation in **8.46 seconds**;
- an automated network-disabled full-stack pass with **94 tests**, all external probes unreachable and local-model inference measured at **9.52 seconds**.

The local model does **not** write factual review prose. It classifies the supervisor's
question as in-scope or out-of-scope; Python renders factual wording from verified evidence.
The model has no review-write tool.

See [verification evidence](docs/verification.md), [browser guide](docs/browser.md) and
[model evaluation](docs/model-evaluation.md).

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

## Install and verify MCP/web integration

Use your existing virtual environment, or create one with `python -m venv .venv` first:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_local.py --integration
.\.venv\Scripts\python.exe scripts/check_web.py
```

Stop on an error. Missing dependencies return a non-zero status, never a successful skip.
Both integration checks use temporary databases.

## Open the local browser workspace

Without AI:

```powershell
.\.venv\Scripts\python.exe scripts/run_web.py
```

With the tested local model:

```powershell
.\.venv\Scripts\python.exe scripts/run_web.py --model "qwen2.5:1.5b"
```

Open the full local session link printed in the terminal and keep its token private.
Create or reopen a synthetic review, select a finding and use the evidence panel. Human-approved
writes use the trusted local control surface; validation and evidence reads use MCP.

The launcher starts a dedicated loopback Ollama service with cloud access disabled. It does
not download a model or silently substitute a hosted API.

## Release hardening

The tested Windows dependency snapshot is committed and the automated network-disabled
full-stack proof has passed. The offline gate confirmed that external probes were unreachable
before exercising MCP, web, SQLite, local AI and a human-confirmed review using only local
services and synthetic temporary state.

Next gates:

```powershell
$py = ".\\.venv\\Scripts\\python.exe"

# Fresh temporary environment + installed-package verification
& $py scripts/check_clean_install.py

# 16 balanced questions x 2 repeats = 32 real local classifications
& $py scripts/evaluate_intent.py --model "qwen2.5:1.5b" --repeats 2
```

The first writes `runtime/clean-install-result.json`. The second writes
`runtime/intent-eval.json` and requires >=90% overall accuracy and >=85% recall
for each intent class.

See [release-hardening procedure](docs/release-hardening.md) and
[model evaluation](docs/model-evaluation.md).

Remaining work includes executing those two gates, expanded rules/reporting and the
final demo/submission materials.

## Cost, privacy and licence

No GitHub Actions workflow is required or dispatched. Budget-blocked jobs are not treated
as test passes or code failures; no billing/protection setting is changed. Runtime uses
your existing computer and SQLite, excluding electricity and connectivity costs. No hosted
database, cloud compute or paid inference service is required.

Do not tunnel/expose these services or commit real records, databases, model weights,
credentials or raw logs. The local database is not encrypted or tamper-proof. The prototype
has not had a production security/privacy audit.

Apache-2.0: the original `LICENSE` is preserved.
