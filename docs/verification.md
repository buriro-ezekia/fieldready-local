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

Under the current architecture, the local model classifies the question as in-scope or
out-of-scope. Python renders the factual explanation from verified evidence. This design was
introduced after earlier free-form model output produced unsupported speculation.

## What this establishes

The following core pathway has now been demonstrated on Windows:

**browser -> real MCP evidence -> local AI intent classification -> deterministic grounded
explanation -> human-controlled review decision**

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

## Remaining release-hardening gates

The core pathway, dependency snapshot and automated offline proof are verified. Remaining:

1. Run packaging/install verification from a clean environment.
2. Expand measured model evaluation beyond the single demonstrated in-scope question,
   including out-of-scope intent accuracy and repeated latency measurements.
3. Optionally retain a screenshot confirming browser rendering while external networking
   is disabled, without exposing the private session token.
4. Expand rules/reporting beyond the synthetic four-column prototype as planned.
5. Prepare final demo-video, product-feedback and friction-log evidence.

## GitHub Actions boundary

No GitHub Actions workflow is required for this evidence. The maintainer reports an Actions
budget limitation. A budget-blocked job is neither a code failure nor a successful test.
Local verification remains the source of truth for the current development workflow.

## Historical implementation-environment evidence

The initial foundation was tested in Linux/Python 3.13.5 with 41 passing tests. Subsequent
browser/model unit checks were also run in the implementation environment with explicit stubs.
Those historical checks did not establish Windows MCP, browser rendering or real inference;
the maintainer-supplied Windows evidence above now covers those core gates.
