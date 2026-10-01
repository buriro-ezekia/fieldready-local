# Working rules

Use the existing Apache-2.0 licence; do not replace it with the proposed MIT licence.
Work on feature branches and use a pull request. Preserve unrelated files and changes.

The maintainer reports GitHub Actions budget-limit failures. Do not create automatic
Actions workflows, increase budgets, request paid services or repeatedly rerun blocked
jobs. Use local verification. A budget-blocked run is not evidence of a code failure
or a pass. Inspect the particular run before attributing its cause. Do not change
repository billing, visibility or protection settings without approval.

Use synthetic data only. Do not commit imported records, databases, model weights,
credentials, private session links or raw respondent logs. Python computes findings.
Python decides question scope deterministically. The local model only classifies a non-critical review focus for in-scope questions; deterministic Python renders factual review text. Never let a model execute shell commands or save review decisions.

Report exactly what ran. Core tests do not prove MCP execution. An MCP import or adapter
is not a demonstrated HTTP integration. Mocked text is not local inference. Do not
fabricate a lockfile, metrics, offline result or Windows test.

Maintainer-supplied Windows evidence verifies the core pathway:
browser -> deterministic scope guard -> real MCP evidence -> local AI review-focus classification -> deterministic grounded explanation -> human-controlled review decision. Historical direct-Ollama evidence observed qwen2.5:1.5b at 8.46 seconds. A later 1 October 2026 browser observation on main verified the reusable local AI service path at 127.0.0.1:8082 with qwen2.5:3b, focus combined, 18.42 seconds elapsed, observed 5 / expected 4 evidence, and no AI-written review decision. See docs/local-ai-service-verification.md.

The maintainer-generated exact-version dependency snapshot is committed. Offline and clean-install gates passed on an earlier branch head; because the router later changed, rerun both on the final head after the focus benchmark passes. Do not overstate this
as manual browser-rendering-while-offline evidence unless a separate visual observation is
recorded. Clean-install/package verification and broader intent/latency evaluation are the
next evidence gates; do not mark them complete before maintainer execution. See
docs/release-hardening.md and docs/model-evaluation.md.

No live Alexa+ integration or Amazon certification is claimed.
