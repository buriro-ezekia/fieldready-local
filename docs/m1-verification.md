# M1 verification record — 28 September 2026

## Scope

This record covers the `feat/versioned-rules-reporting` branch and the richer
`field-survey-v1.0.0` workflow. Results below were supplied from the maintainer's Windows
environment. They are not a rerun inside the implementation environment.

## Local regression suite

Reported result:

- **115 tests passed**;
- elapsed time: **8.229 seconds**;
- final status: `OK`;
- `CORE CHECKS: PASS`.

As labelled by the script itself, the core suite alone is not evidence of MCP, browser or
local-model execution.

## M0 compatibility integrations

The existing foundation remained compatible after the M1 storage/ruleset changes.

### MCP

- negotiated protocol: **2026-07-28**;
- original synthetic household demo: 8 rows / 6 findings / 6 affected records;
- persisted review after restart: 1 confirmed / 5 unresolved;
- result: `MCP HTTP + RESTART PERSISTENCE: PASS`.

### Web -> MCP -> SQLite

- MCP health tool surface remained exactly:
  - `get_review_summary`;
  - `list_findings`;
  - `validate_batch`;
- result: `WEB HTTP -> MCP -> SQLITE + RESTART: PASS`.

## M1 real integration

The dedicated `scripts/check_m1_integration.py` gate passed through the real MCP server,
browser backend, SQLite persistence, local report exporter and service restart.

Observed M1 evidence:

- MCP protocol: **2026-07-28**;
- ruleset: `field-survey-v1.0.0`;
- rows: **14**;
- findings: **17**;
- affected rows: **13**;
- severity:
  - critical: **3**;
  - high: **9**;
  - medium: **5**;
- rule evaluations:
  - evaluable: **80**;
  - not evaluable: **5**;
- one explicit confirmed review left **16 unresolved findings**;
- review-package files:
  - `summary.md`;
  - `findings.csv`;
  - `review_history.csv`;
  - `manifest.json`;
- raw source CSV included: **false**;
- MCP tools remained exactly the same three bounded read/validate tools.

Final result:

`M1 REAL MCP + WEB + EXPORT + RESTART: PASS (browser rendering and local-model inference NOT tested)`

## Manual browser observation

The maintainer also supplied a browser screenshot from the richer field-survey workflow.

The screenshot visibly confirms:

- saved review labelled `field-survey-v1.0.0`;
- records: **14**;
- findings: **17**;
- affected records: **13**;
- unresolved findings: **16**;
- ruleset title: Synthetic field-survey quality rules;
- ruleset version: **1.0.0**;
- rule evaluations: **80 evaluable / 5 not evaluable**;
- severity: **critical 3, high 9, medium 5**;
- the browser displayed a successful local export notice;
- that notice explicitly stated that the raw source CSV was not included.

This establishes actual browser rendering and manual use of the local export action for M1.

### Reusable local AI browser observation — 1 October 2026

A later maintainer-supplied Windows browser observation closes the earlier M1
local-model-inference gap. After pull request #7 was merged to `main`, FieldReady reported:

```text
AI: qwen2.5:3b via reusable service 127.0.0.1:8082
```

For the richer `household.component_total` finding at record ordinal 2, the browser showed
observed `household_size = 5`, expected component total `4`, model `qwen2.5:3b`, focus
`combined`, elapsed time **18.42 seconds**, and an explicit notice that **no review decision
was saved**. Scope remained deterministic and Python rendered the factual explanation from
verified evidence.

See [reusable local AI browser verification](local-ai-service-verification.md) for the
evidence boundary and routing-source detail.

## What M1 now establishes

The following path is verified on Windows:

**versioned synthetic ruleset -> immutable ruleset-bound batch -> real MCP validation ->
rich evidence -> browser review -> explicit human decision -> local supervisor export ->
restart persistence**

M1 does not add export, filesystem, shell, SQL or review-write capabilities to the MCP tool
surface.

## Evidence boundaries

- Synthetic data only.
- No live Alexa+ integration or Amazon certification is claimed.
- No GitHub Actions result is required for this evidence.
- No paid hosted database, deployment service or external inference API is required.
- The report package excludes the raw source CSV.
- Browser local-model inference for the richer M1 ruleset remains a separate visual/manual
  observation if desired for the final demo.
