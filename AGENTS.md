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
The local model only classifies question scope; deterministic Python renders factual
review text. Never let a model execute shell commands or save review decisions.

Report exactly what ran. Core tests do not prove MCP execution. An MCP import or adapter
is not a demonstrated HTTP integration. Mocked text is not local inference. Do not
fabricate a lockfile, metrics, offline result or Windows test.

Maintainer-supplied Windows evidence now verifies the core pathway:
browser -> real MCP evidence -> local AI intent classification -> deterministic grounded
explanation -> human-controlled review decision. Real qwen2.5:1.5b inference was observed
at 8.46 seconds for the demonstrated question.

Release hardening remains separate from the verified core. scripts/write_lock.py must
generate the exact-version snapshot from the maintainer's tested virtual environment;
do not hand-author requirements.lock.txt or docs/environment-lock.json. scripts/check_offline.py
must run while external connectivity probes are unavailable before offline status is
claimed. See docs/release-hardening.md.

No live Alexa+ integration or Amazon certification is claimed.
