# Local setup

FieldReady Local is a local-first hackathon prototype using synthetic data only. The
verified Windows environment is CPython **3.14.6**; the project requires Python 3.11+.

The richer submission workflow has been verified on Windows through core tests, real MCP,
browser -> MCP -> SQLite integration, versioned survey rules/reporting, restart persistence,
local export and final submission hygiene checks.

## 1. Clone and create a virtual environment

From the repository root in PowerShell:

```powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
```

Install the MCP/browser runtime:

```powershell
& $py -m pip install -e ".[mcp]"
& $py -m pip check
```

For reproducibility, the tested Windows dependency snapshot is committed in
`requirements.lock.txt` with metadata in `docs/environment-lock.json`.

The lock is an exact-version environment snapshot, not a hash-locked wheel supply-chain
manifest.

## 2. Run the deterministic core checks

```powershell
& $py scripts/check_local.py
```

The current richer branch includes **115 regression tests** in the maintainer-verified M1
run.

The original household demo remains available:

```powershell
& $py scripts/fieldready.py demo
```

The richer hackathon demonstration is:

```powershell
& $py scripts/fieldready.py demo-field
```

Its fixed synthetic answer key is:

- 14 records;
- 17 findings;
- 13 affected records;
- severity: 3 critical / 9 high / 5 medium;
- 80 evaluable / 5 not-evaluable rule applications.

## 3. Run the real MCP/browser integration checks

```powershell
& $py scripts/check_local.py --integration
& $py scripts/check_web.py
& $py scripts/check_m1_integration.py
```

The verified local MCP path negotiates protocol **2026-07-28** and exposes exactly:

- `validate_batch`;
- `list_findings`;
- `get_review_summary`.

No model-facing review-write, export, shell, SQL, arbitrary-filesystem or network-fetch tool
is exposed.

## 4. Open the browser workspace

Without local AI:

```powershell
& $py scripts/run_web.py
```

With the tested direct local Ollama model:

```powershell
& $py scripts/run_web.py --model "qwen2.5:1.5b"
```

With the reusable local AI service already running on port 8082:

```powershell
& $py scripts/run_web.py --ai-service-port 8082 --model "qwen2.5:3b"
```

See `docs/local-ai-service.md` for the shared-gateway architecture and verification boundary.

The launcher:

1. generates private local credentials;
2. starts the MCP server on `127.0.0.1`;
3. verifies the MCP handshake and exact tool surface;
4. either starts a dedicated local Ollama service with `OLLAMA_NO_CLOUD=1`, or verifies the
   explicitly selected loopback local AI service;
5. prints a private localhost session link;
6. launches no cloud fallback.

Open the full session link locally. The browser stores the token in session storage and
removes it from the visible address bar. Keep the original printed link private.

The browser header displays the negotiated MCP protocol and tool count so the runtime
integration is visible during the demo.

## 5. Review workflow

Use **Field-survey demo** for the hackathon presentation.

The review workflow is:

**versioned ruleset -> MCP validation/evidence -> deterministic explanation -> optional
bounded local AI -> explicit human decision -> local review package**

A review decision requires:

- finding ID;
- permitted status;
- reason;
- current revision;
- unique request ID;
- explicit confirmation.

Confirmed means **reviewed**, not corrected. The imported source CSV is never edited by a
review action.

SQLite schema version **2** stores the ruleset binding and migrates existing v1 databases by
assigning them the legacy `synthetic-household-v0.1` ruleset.

Do not point the prototype at a production or confidential database.

## 6. Export a supervisor review package

CLI:

```powershell
& $py scripts/fieldready.py export RUN_ID .\runtime\review-package
```

The browser also exposes **Export review package**, but writes only to its
application-controlled local export directory.

The package contains:

- `summary.md`;
- `findings.csv`;
- `review_history.csv`;
- `manifest.json`.

The raw source CSV is deliberately excluded.

## 7. Optional local-model checks

The model is not required for deterministic validation/review/export.

If `qwen2.5:1.5b` is already installed locally:

```powershell
& $py scripts/check_model.py --model "qwen2.5:1.5b"
& $py scripts/evaluate_intent.py --model "qwen2.5:1.5b" --repeats 2
```

FieldReady does not automatically download a model and does not silently fall back to a
hosted model.

Python owns scope and factual wording. The local model is used only for non-critical
review-focus classification after deterministic scope acceptance.

## 8. Release/submission checks

Clean-install/package check:

```powershell
& $py scripts/check_clean_install.py
```

Explicit network-disabled full-stack check:

```powershell
& $py scripts/check_offline.py --model "qwen2.5:1.5b"
```

Final hackathon repository audit:

```powershell
& $py scripts/check_submission.py
```

The final submission audit is intentionally required to run from `main`, because judges
opening the submitted repository URL should land directly on the verified application rather
than an empty or development-only default branch.

## 9. Manual MCP server start

For development outside `run_web.py`:

```powershell
$env:FIELDREADY_MCP_TOKEN = (& $py -c "import secrets; print(secrets.token_urlsafe(32))")
& $py -m fieldready.mcp_server
```

Default endpoint:

`http://127.0.0.1:8000/mcp`

Clients must send:

`Authorization: Bearer <locally generated token>`

Never paste the generated token into prompts, commits, screenshots or public issues.

## 10. Evidence boundaries

A passing unit suite is not described as proof of browser/model/MCP execution. FieldReady
keeps these evidence types separate:

- core tests;
- real MCP HTTP/protocol execution;
- browser -> MCP -> SQLite integration;
- local model execution;
- explicit network-disabled operation;
- clean-install/package verification;
- manual browser observation.

See:

- `docs/verification.md`;
- `docs/m1-verification.md`;
- `docs/release-hardening.md`;
- `docs/model-evaluation.md`;
- `docs/rulesets.md`.

## Failure classification

| Observation | Interpretation |
| --- | --- |
| A test prints a failing assertion | Investigate the code, test or assumptions. |
| MCP check says dependencies are missing | Integration did not run; install and retry locally. |
| A GitHub Actions job is blocked by budget | Infrastructure constraint; no code result was produced. |
| CLI works but MCP/browser/model was not exercised | Core evidence only, not full-stack evidence. |
| Final submission audit is run off `main` | Merge the verified submission branch first, then rerun. |

No GitHub Actions workflow is required for the demonstrated local verification path.
