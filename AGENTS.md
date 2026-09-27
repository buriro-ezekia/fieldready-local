# Working rules

Use the existing Apache-2.0 licence; do not replace it with the proposed MIT licence.
Work on feature branches and use a pull request. Preserve unrelated files and changes.

The maintainer reports GitHub Actions budget-limit failures. Do not create automatic
Actions workflows, increase budgets, request paid services or repeatedly rerun blocked
jobs. Use `python scripts/check_local.py`. A budget-blocked run is not evidence of a
code failure or a pass. Inspect the particular run before attributing its cause.
Do not change repository billing, visibility or protection settings without approval.

Use synthetic data only. Do not commit imported records, databases, model weights,
credentials or raw respondent logs. Python computes findings; a model may explain them.
Never let a model execute shell commands or save review decisions.

Report exactly what ran. Core tests do not prove MCP execution. An MCP import or
adapter is not a demonstrated HTTP integration. Mocked text is not local inference.
Do not fabricate a lockfile, metrics, an offline check or Windows test results.
No live Alexa+ integration or Amazon certification is claimed.

M0 remains open. The maintainer has reported 41 passing Windows core tests and a
successful real MCP/restart check (protocol 2026-07-28). The browser and explanation
connector are now implemented, with 38 additional unit tests using explicit stubs.
The new web-to-MCP path, browser rendering, actual local inference and full offline
workflow remain verification gates. See docs/browser.md for current evidence and
commands; docs/verification.md retains the initial foundation record.
