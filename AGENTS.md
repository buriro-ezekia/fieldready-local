# Working rules

Use the existing Apache-2.0 licence; do not replace it with the proposed MIT licence.
Work on feature branches and use a pull request. Preserve unrelated files and changes.

The maintainer reports GitHub Actions budget-limit failures. Do not create automatic
Actions workflows, increase budgets, request paid services or repeatedly rerun blocked
jobs. Use `python scripts/check_local.py`. A budget-blocked run is not evidence of a
code failure or a pass. Inspect the particular run before attributing its cause.
Do not change repository billing, visibility or protection settings without approval.

Use synthetic data only. Do not commit imported records, databases, model weights,
credentials or raw respondent logs. Python computes findings; a future model may
explain them. Never let a model execute shell commands or save review decisions.

Report exactly what ran. Core tests do not prove MCP execution. An MCP import or
adapter is not a demonstrated HTTP integration. Mocked text is not local inference.
Do not fabricate a lockfile, metrics, an offline check or Windows test results.
No live Alexa+ integration or Amazon certification is claimed.

Current contribution is only the foundation of M0. Complete real MCP HTTP checks,
then the UI/model workflow, before representing M0 as complete. Dependency downloads
were unavailable in the initial implementation environment. See docs/verification.md.
