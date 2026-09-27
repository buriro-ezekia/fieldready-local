# First milestone backlog

| Order | Task | Status / acceptance evidence |
| --- | --- | --- |
| 1 | Core validation, storage and local checks | **Complete.** Synthetic fixtures and local test suite pass. |
| 2 | Execute and repair the SDK integration | **Complete.** Real HTTP MCP handshake, protocol 2026-07-28, expected counts and restart persistence passed on Windows. |
| 3 | Resolve dependency environment | **Complete.** The maintainer generated the tested Windows exact-version snapshot; `requirements.lock.txt` and `docs/environment-lock.json` are committed. Metadata reports Python 3.14.6, 30 packages, required MCP roots present and `pip check` pass. |
| 4 | Minimal browser interface | **Complete.** Windows browser displayed evidence retrieved through the real MCP path. |
| 5 | Trusted UI decision path | **Complete.** Explicit human decision saved; persisted review state observed; source CSV unchanged. |
| 6 | Actual local-model assistance | **Core gate complete.** Real qwen2.5:1.5b inference observed; 8.46 s for the demonstrated in-scope question. Model only classifies scope; Python renders factual evidence. Broader evaluation remains pending. |
| 7 | Windows/offline proof | **Automated offline gate complete.** External probes were unreachable; 94 tests, real MCP/web/SQLite, qwen2.5:1.5b local inference (9.52 s), grounded output and confirmed-review persistence all passed. Manual offline browser rendering remains optional visual evidence. |
| 8 | Expand rules and reporting | **Pending.** Add versioned rules, tested exports and clear denominators for a stronger submission demo. |

## Verified core pathway

**browser -> real MCP evidence -> local AI intent classification -> deterministic grounded
explanation -> human-controlled review decision**

Do not equate this with final submission readiness. Clean-install verification, broader evaluation and submission artefacts remain open.

No automated GitHub Actions workflow is required while the agreed development path remains
local-first and independent of the maintainer's Actions budget.
