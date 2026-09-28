# FieldReady Local

A local survey-review assistant for the Amazon Developer Hackathon: a **simulated
Alexa+ experience with a real local MCP backend**, not a live Alexa+ integration or
an Amazon-certified application. Use synthetic data only.

## Current status — verified local-first review workflow

The current Windows-verified product path is:

**browser -> live MCP evidence -> deterministic scope -> optional local AI review-focus classification -> deterministic grounded explanation -> explicit human decision -> local audit export**

The richer `field-survey-v1.0.0` workflow has been exercised through real MCP, the browser
backend, SQLite persistence, report export and service restart. Maintainer-supplied evidence
includes:

- **115 passing M1 tests**;
- negotiated MCP protocol **2026-07-28**;
- the exact three-tool MCP surface:
  `validate_batch`, `list_findings`, `get_review_summary`;
- richer synthetic demo: **14 records / 17 findings / 13 affected records**;
- severity: **3 critical / 9 high / 5 medium**;
- **80 evaluable / 5 not-evaluable** rule applications;
- one explicit human decision persisting after restart;
- four-file local review package with the raw source CSV excluded;
- manual browser rendering and successful local export;
- a separate explicit network-disabled full-stack pass with local Ollama inference.

The browser now shows the **live negotiated MCP protocol and tool count** directly in the
header, so the required technology is visible in the product rather than only in terminal
logs.

The local model does **not** control scope, author factual findings or save decisions.
Python owns scope and factual evidence. For accepted review questions, the local model only
classifies a non-critical review focus; Python renders the explanation from verified rule
evidence.

See [M1 verification](docs/m1-verification.md), [verification history](docs/verification.md),
[model evaluation](docs/model-evaluation.md) and [versioned rules](docs/rulesets.md).

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

**Public demo video:** https://youtu.be/DfNdp4d5lhs

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
- [the requirements-to-evidence map](docs/submission-requirements-map.md) for final coverage;
- [the YouTube upload package](docs/youtube-upload.md) for title, description and upload checks.

Before submitting, run the repository audit:

```powershell
.\.venv\Scripts\python.exe scripts/check_submission.py --hygiene-only
```

The mini-challenge choice and pre-existing-work disclosure are now confirmed. The
hygiene-only pass checks tracked repository safety while allowing the **public demo video
URL** to remain temporarily unresolved. After the video is uploaded and its URL is inserted,
the final submission audit without `--hygiene-only` must pass.

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

## Verification and reproducibility

FieldReady Local separates evidence types rather than treating one test suite as proof of
everything:

- core unit/regression checks;
- real MCP protocol/tool execution;
- web -> MCP -> SQLite integration;
- local-model execution;
- explicit network-disabled operation;
- versioned-rules/reporting integration;
- manual browser observation.

The tested Windows dependency snapshot is committed in `requirements.lock.txt` with
metadata in `docs/environment-lock.json`. A fresh-environment install/package check was
also demonstrated during release hardening.

For the current richer workflow, use:

```powershell
$py = ".\.venv\Scripts\python.exe"

& $py scripts/check_local.py
& $py scripts/check_m1_integration.py
& $py scripts/check_submission.py --hygiene-only
```

See [release hardening](docs/release-hardening.md) and
[M1 verification](docs/m1-verification.md) for the evidence boundaries. The remaining
submission blocker is operational, not architectural: record/upload the public <3 minute
demo and insert its URL into `docs/devpost-submission.md`.

## Cost, privacy and licence

No GitHub Actions workflow is required or dispatched. Budget-blocked jobs are not treated
as test passes or code failures; no billing/protection setting is changed. Runtime uses
your existing computer and SQLite, excluding electricity and connectivity costs. No hosted
database, cloud compute or paid inference service is required.

Do not tunnel/expose these services or commit real records, databases, model weights,
credentials or raw logs. The local database is not encrypted or tamper-proof. The prototype
has not had a production security/privacy audit.

Apache-2.0: the original `LICENSE` is preserved.
