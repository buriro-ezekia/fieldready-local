# First milestone backlog

| Order | Task | Status / acceptance evidence |
| --- | --- | --- |
| 1 | Core validation, storage and local checks | **Complete.** Synthetic fixtures and local test suite pass. |
| 2 | Execute and repair the SDK integration | **Complete.** Real HTTP MCP handshake, protocol 2026-07-28, expected counts and restart persistence passed on Windows. |
| 3 | Resolve dependency environment | **Complete.** The maintainer generated the tested Windows exact-version snapshot; `requirements.lock.txt` and `docs/environment-lock.json` are committed. Metadata reports Python 3.14.6, 30 packages, required MCP roots present and `pip check` pass. |
| 4 | Minimal browser interface | **Complete.** Windows browser displayed evidence retrieved through the real MCP path. |
| 5 | Trusted UI decision path | **Complete.** Explicit human decision saved; persisted review state observed; source CSV unchanged. |
| 6 | Actual local-model assistance | **Core local-AI gate complete; final focus benchmark pending.** Real qwen2.5:1.5b inference was observed. The model no longer controls scope; it only classifies advisory review focus after deterministic scope acceptance. |
| 7 | Windows/offline proof | **Previously passed; current-head rerun required.** The pre-hybrid branch passed the automated offline gate with external probes unreachable, 94 tests, real MCP/web/SQLite and qwen2.5:1.5b. Because the production router changed afterwards, rerun the offline gate on the final hybrid head before submission. |
| 8 | Clean install / packaging | **Previously passed; current-head rerun required.** The fresh-environment gate passed before the hybrid router change (30-package snapshot, 8 rows / 6 findings, package assets, setuptools 84.0.0). Rerun once after the hybrid benchmark passes to bind packaging evidence to the final head. |
| 9 | Broader intent/latency evaluation | **Two failures drove the final design; final rerun pending.** Raw model: 50% accuracy / 0% out-of-scope recall. First hybrid: routing 100% but scope accuracy 81.25% because the model denied 6 legitimate review queries. Final design makes scope fully deterministic and AI focus advisory. Rerun must achieve 100% scope/routing and >=75% focus accuracy. |
| 10 | Expand rules and reporting | **Pending.** Add versioned rules, tested exports and clear denominators for a stronger submission demo. |

## Verified core pathway

**browser -> real MCP evidence -> local AI intent classification -> deterministic grounded
explanation -> human-controlled review decision**

Do not equate this with final submission readiness. Broader evaluation and submission artefacts remain open.

No automated GitHub Actions workflow is required while the agreed development path remains
local-first and independent of the maintainer's Actions budget.
