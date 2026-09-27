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

## Remaining release-hardening gates

The core pathway is verified, but the project is not yet submission-ready. The following
remain open:

1. Generate and commit a reproducible dependency lock from the tested environment.
2. Perform an explicit **network-disabled** end-to-end run after all dependencies and the
   local model are already installed.
3. Run packaging/install verification from a clean environment.
4. Expand measured model evaluation beyond the single demonstrated in-scope question,
   including out-of-scope intent accuracy and repeated latency measurements.
5. Expand rules/reporting beyond the synthetic four-column prototype as planned.
6. Prepare final demo-video, product-feedback and friction-log evidence.

## GitHub Actions boundary

No GitHub Actions workflow is required for this evidence. The maintainer reports an Actions
budget limitation. A budget-blocked job is neither a code failure nor a successful test.
Local verification remains the source of truth for the current development workflow.

## Historical implementation-environment evidence

The initial foundation was tested in Linux/Python 3.13.5 with 41 passing tests. Subsequent
browser/model unit checks were also run in the implementation environment with explicit stubs.
Those historical checks did not establish Windows MCP, browser rendering or real inference;
the maintainer-supplied Windows evidence above now covers those core gates.
