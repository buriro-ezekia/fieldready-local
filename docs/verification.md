# Verification record — 27 September 2026

## Current Windows evidence supplied by the maintainer

The following checks were executed on the maintainer's Windows environment against the
`feat/mcp-validation-slice` branch. These are maintainer-supplied results, not a rerun
inside the implementation environment.

### Core and MCP

- **85 tests passed** after the first structured-output hardening pass. A later test count may
  increase as additional safeguards are added; the important criterion is the reported `OK`.
- Real MCP negotiated protocol **2026-07-28**.
- The synthetic batch returned **8 records, 6 findings affecting 6 records**.
- Component-total evaluation was available for 6 records and unavailable for records 6 and 7.
- A confirmed review persisted after the MCP server restarted: **1 confirmed, 5 unresolved**.
- The real integration check ended with:
  `MCP HTTP + RESTART PERSISTENCE: PASS`.

### Web -> MCP -> SQLite

The maintainer ran the real web integration check. It returned the expected synthetic counts,
preserved one confirmed finding after restart and ended with:

`WEB HTTP -> MCP -> SQLITE + RESTART: PASS (browser rendering and local inference NOT tested)`

This established the real HTTP -> MCP -> SQLite integration independently of browser rendering.

### Browser review workflow

The browser workspace was opened successfully on Windows. The maintainer demonstrated:

- the saved synthetic review reopening correctly;
- 8 records, 6 findings and 6 affected records;
- two confirmed findings and **4 unresolved findings** after manual review;
- the component-total evidence showing observed **5** and expected **4**;
- an explicit human-confirmed review decision;
- the original CSV remaining unchanged.

### Real local AI interaction

The browser was launched with the already installed local model `qwen2.5:1.5b`.

For the selected `component_total` finding, the supervisor asked:

> Why is this record flagged, and what should I verify?

The browser returned:

> Rule component_total · record ordinal 2. The finding was raised because household_size is
> recorded as 5, while the validated component total is 4. Verification: check the source
> component values and household_size before recording a review outcome.

The interface also reported:

- local model: `qwen2.5:1.5b`;
- elapsed time: **8.46 seconds**;
- evidence reference ending in `:1 / component_total`;
- no review decision was saved by the AI path.

Under the current architecture, Python decides scope deterministically. Only in-scope review questions reach the local model, which classifies a non-critical review focus. Python renders the factual explanation from verified evidence. This design was
introduced after earlier free-form model output produced unsupported speculation.

## What this establishes

The following core pathway has now been demonstrated on Windows:

**browser -> deterministic scope guard -> real MCP evidence -> local AI review-focus classification -> deterministic grounded explanation -> human-controlled review decision**

The model has no review-write tool and does not edit source records.

## Tested dependency snapshot

The maintainer generated the exact-version snapshot from the tested Windows virtual
environment and supplied both generated files. The committed metadata reports:

- Python 3.14.6 / CPython on Windows;
- 30 exact package pins;
- required roots `httpx2`, `mcp` and `uvicorn` present;
- `pip check`: pass;
- lock SHA-256:
  `60c438efebbfe9bf42df6b84bf5b35c759c937188bb5d4f7b533e1eb772f6fb2`.

The supplied metadata hash was independently checked against the supplied
`requirements.lock.txt` before commit. This is an exact-version environment snapshot,
not a hash-locked wheel supply-chain manifest.

## Explicit network-disabled full-stack proof

The maintainer supplied the output from `scripts/check_offline.py --model "qwen2.5:1.5b"`
while external networking was unavailable.

Evidence recorded by that run:

- `pip check`: no broken requirements;
- **94 tests passed** in 3.826 seconds;
- MCP protocol **2026-07-28** negotiated;
- MCP HTTP + restart persistence: pass;
- web HTTP -> MCP -> SQLite + restart: pass;
- external probes to 1.1.1.1:443, 8.8.8.8:53 and github.com:443 were all unreachable;
- local model: `qwen2.5:1.5b`;
- measured local intent inference: **9.52 seconds**;
- grounded `component_total` explanation matched observed 5 / expected 4 evidence;
- AI explanation did not write a review decision;
- explicit confirmed review changed unresolved findings through the trusted review path;
- final result: `OFFLINE FULL STACK: PASS`.

This establishes automated operation of MCP, web backend, SQLite, local AI and the
human-controlled decision path without external connectivity once dependencies and the
local model are installed. It does not by itself establish browser rendering while offline;
that remains a separate visual/manual observation.

## Clean-install and packaging verification

The maintainer ran `scripts/check_clean_install.py` successfully on Windows using the
committed dependency snapshot.

The fresh temporary environment reported:

- Python **3.14.6**;
- runtime lock SHA-256
  `60c438efebbfe9bf42df6b84bf5b35c759c937188bb5d4f7b533e1eb772f6fb2`;
- **30** exact runtime package pins;
- build backend resolved to `setuptools 84.0.0`;
- installed synthetic demo returned **8 rows** and **6 findings**;
- packaged CSV and browser assets: `PACKAGE DATA: PASS`;
- final result: `CLEAN INSTALL + PACKAGING: PASS`.

Windows also reported that the temporary virtual-environment executable resolved from an
8.3 short pathname to the corresponding long pathname. This was informational path
normalisation and did not affect the successful installed-package checks.

## Broader routing/model evaluation history

Two broader evaluations exposed weaknesses and drove the final router design.

**Raw binary model classifier:** 32 evaluations, 50% accuracy, in-scope recall 1.00,
out-of-scope recall 0.00. The model predicted in-scope for every question.

**First hybrid router:** deterministic routing was perfect (32/32), but the model still
controlled the final in-scope/out-of-scope result for review-related questions. It achieved
26/32 overall (81.25%), with in-scope recall 0.625 and out-of-scope recall 1.00. Six
legitimate review questions were denied by the model. Mean model latency was 1.856 s,
median 1.39 s, p95 7.95 s.

The final production design therefore removes scope authority from the model entirely.
Python's deterministic scope guard makes the final in-scope/out-of-scope decision. In-scope
questions then reach qwen2.5:1.5b only for an advisory review-focus classification
(reason, verification, evidence, review_guidance, or combined). Factual text remains
deterministic.

A final benchmark rerun is pending. It must show 100% scope/routing accuracy and at least
75% review-focus accuracy on the in-scope cases.

## Remaining release-hardening gates

The core pathway and dependency snapshot are verified. Earlier offline and clean-install passes are retained as historical evidence but must be rerun on the final router head. Remaining:

1. Expand measured model evaluation beyond the single demonstrated in-scope question,
   including out-of-scope intent accuracy and repeated latency measurements.
2. Optionally retain a screenshot confirming browser rendering while external networking
   is disabled, without exposing the private session token.
3. Expand rules/reporting beyond the synthetic four-column prototype as planned.
4. Prepare final demo-video, product-feedback and friction-log evidence.

## GitHub Actions boundary

No GitHub Actions workflow is required for this evidence. The maintainer reports an Actions
budget limitation. A budget-blocked job is neither a code failure nor a successful test.
Local verification remains the source of truth for the current development workflow.

## Historical implementation-environment evidence

The initial foundation was tested in Linux/Python 3.13.5 with 41 passing tests. Subsequent
browser/model unit checks were also run in the implementation environment with explicit stubs.
Those historical checks did not establish Windows MCP, browser rendering or real inference;
the maintainer-supplied Windows evidence above now covers those core gates.
