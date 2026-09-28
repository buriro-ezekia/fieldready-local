# FieldReady Local

A local survey-review assistant for the Amazon Developer Hackathon: a **simulated
Alexa+ experience with a real local MCP backend**, not a live Alexa+ integration or
an Amazon-certified application. Use synthetic data only.

## Current status — core and automated offline workflow verified

The maintainer has demonstrated the core workflow on Windows:

**browser -> deterministic scope guard -> real MCP evidence -> local AI review-focus classification -> deterministic grounded explanation -> human-controlled review decision**

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

The local model does **not** decide whether a question is allowed and does **not** write factual review prose. Python decides scope deterministically. Only in-scope review questions reach the local model, which classifies a non-critical review focus such as reason, verification, evidence or review guidance. Python renders all factual wording from verified evidence. The model has no review-write tool.

See [verification evidence](docs/verification.md), [browser guide](docs/browser.md) and
[model evaluation](docs/model-evaluation.md).

## M1 branch — versioned rules and supervisor reporting

The `feat/versioned-rules-reporting` branch adds a second, richer synthetic workflow while
preserving the original four-column demo for regression evidence.

New M1 capabilities:

- packaged, versioned rulesets bound to each imported batch;
- SQLite schema v2 with automatic v1 migration;
- richer field-survey demo with 14 fictional records;
- expected answer key: **17 findings affecting 13 records**;
- severity summary: **3 critical, 9 high, 5 medium**;
- completeness, uniqueness, validity, consistency, interview-duration and GPS checks;
- explicit not-evaluable rule applications rather than silent passes;
- deterministic rule-specific explanation and verification text;
- ruleset-aware browser import and saved-review labels;
- local export of `summary.md`, `findings.csv`, `review_history.csv` and `manifest.json`;
- export manifest SHA-256 hashes and **no raw source CSV**;
- fixed browser export directory and unchanged three-tool MCP surface.

The richer demo is intentionally synthetic. User-supplied arbitrary rule JSON is not enabled;
rulesets remain package-owned and test-covered.

Source-checkout examples:

```powershell
python scripts/fieldready.py rulesets
python scripts/fieldready.py demo-field
```

After a run is reviewed:

```powershell
python scripts/fieldready.py export RUN_ID .\runtime\review-package
```

See [versioned rules and reporting](docs/rulesets.md) for the rule/operator contract,
fixture expectations and export privacy boundary.

**M1 Windows verification is complete for the deterministic rules/reporting path.** The maintainer reported 115 passing tests, successful real MCP/web/export/restart integration, and supplied a browser screenshot confirming the 14/17/13 field-survey counts plus successful local export. See [M1 verification evidence](docs/m1-verification.md).

## Judge/demo path

For a concise presentation, start the richer field-survey workflow in the browser and follow
the built-in **2-minute demo path**:

1. Field-survey demo
2. Review next priority
3. Explain with local model
4. Confirm one human decision
5. Export review package

The interface exposes the verified 14 / 17 / 13 headline, review progress, severity and
issue-category summaries while preserving the same M1 backend.

Use:

- [the under-three-minute recording script](docs/demo-script.md) for the video;
- [the visual capture plan](docs/submission-assets.md) for screenshots;
- [the field-by-field Devpost package](docs/devpost-submission.md) for submission text;
- [the requirements-to-evidence map](docs/submission-requirements-map.md) for final coverage.

Before submitting, run the repository audit:

```powershell
.\.venv\Scripts\python.exe scripts/check_submission.py --hygiene-only
```

The hygiene-only pass checks tracked repository safety while allowing the three human
confirmation markers (video URL, mini-challenge choice and pre-existing-work disclosure) to
remain temporarily unresolved. The final submission audit without `--hygiene-only` must
pass after those fields are completed.

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

The tested Windows dependency snapshot is committed. Earlier automated offline and clean-install gates passed before the latest router redesign; they must be rerun once the current focus benchmark passes so final evidence matches the final branch head. The offline gate confirmed that external probes were unreachable
before exercising MCP, web, SQLite, local AI and a human-confirmed review using only local
services and synthetic temporary state.

Next gates:

```powershell
$py = ".\\.venv\\Scripts\\python.exe"

# Fresh temporary environment + installed-package verification
& $py scripts/check_clean_install.py

# 16 balanced questions x 2 repeats = 32 production-router evaluations
& $py scripts/evaluate_intent.py --model "qwen2.5:1.5b" --repeats 2
```

The benchmark writes `runtime/intent-eval.json`. Scope and routing must be perfect because they are deterministic; the advisory local-model focus classifier must reach at least 75% accuracy on the in-scope cases.

See [release-hardening procedure](docs/release-hardening.md) and
[model evaluation](docs/model-evaluation.md).

The M0 release-hardening gates are tracked separately. On the M1 branch, the immediate
next step is to execute the expanded test suite and richer field-survey demo before any
M1 result is promoted to verified evidence.

## Cost, privacy and licence

No GitHub Actions workflow is required or dispatched. Budget-blocked jobs are not treated
as test passes or code failures; no billing/protection setting is changed. Runtime uses
your existing computer and SQLite, excluding electricity and connectivity costs. No hosted
database, cloud compute or paid inference service is required.

Do not tunnel/expose these services or commit real records, databases, model weights,
credentials or raw logs. The local database is not encrypted or tamper-proof. The prototype
has not had a production security/privacy audit.

Apache-2.0: the original `LICENSE` is preserved.
