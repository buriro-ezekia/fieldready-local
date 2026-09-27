# Verification record — 27 September 2026

## Executed in the implementation environment

Environment: Linux, Python 3.13.5. Command: `python scripts/check_local.py`.
Result: **41 tests passed**, no skipped tests. The suite includes 31 rule/storage/CLI
tests and 10 ASGI request-guard tests. Each run uses synthetic data and temporary databases.

The independent fixture expectation is 8 records, 6 findings affecting 6 records,
with component-total evaluation unavailable for records 6 and 7. Expected findings:

| Record ordinal | Rule |
| --- | --- |
| 2 | component_total |
| 3 | duplicate_id |
| 4 | duplicate_id |
| 5 | missing_id |
| 6 | missing_count |
| 7 | invalid_count |

The suite checks UTF-8/BOM, leading-zero IDs, malformed/oversized input, missingness,
multiple findings on one row, pagination, unknown identifiers, source preservation,
source integrity checks, transaction rollback, decision confirmation, request replay,
stale revisions and persistence across separate CLI processes. Guard tests check
credentials, Host, Origin, duplicate security headers and lifespan forwarding.

## Not executed successfully / not yet implemented

- **MCP HTTP:** `python scripts/check_mcp.py` returned status 2 with missing `mcp` and
  `httpx2` dependencies. No real MCP handshake, SDK tool call or restart-through-MCP
  result has been observed. No stubbed protocol result is counted as a pass.
- **Installation and lock:** dependency download failed due to name resolution in
  this environment. Package ranges are not verified pins. `uv.lock` is not fabricated.
- **Browser interface and model:** not implemented in this contribution; no inference,
  model performance, voice, live Alexa+ connection or UI result is claimed.
- **Windows and complete offline workflow:** not tested here. Cross-platform code is
  not the same thing as measured Windows compatibility.
- **GitHub Actions:** no workflow added or dispatched. The maintainer reports a budget
  limitation; no particular failed Actions run was diagnosed in this contribution.
- **Lint/type/packaging:** source parsing is checked separately, but Ruff, static type
  checking and install/build verification have not been run.

## Acceptance gate

This is a foundation contribution, not completed M0. Run the optional integration check
on a dependency-enabled machine, review any failures, resolve/lock versions, and only
then add the browser and real local-model proof. Keep outcomes and pending work separate.
