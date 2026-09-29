# Hackathon requirements-to-evidence map

Basis: the supplied Build, Ship, Shape: Amazon Developer Hackathon requirements page.

This is an internal submission checklist, not a claim of Amazon certification.

## Alexa+ technical route

### Requirement

Alexa+ submissions may use a self-hosted MCP server using specification 2025-11-25 or
later with Streamable HTTP, or build a simulated Alexa+ experience in a web app. The demo
must show the required technology working rather than mentioning it only in documentation.

### FieldReady evidence

| Evidence | Repository location |
| --- | --- |
| Self-hosted MCP server | `src/fieldready/mcp_server.py` |
| Streamable HTTP application | `src/fieldready/mcp_server.py` |
| Exact bounded MCP client | `src/fieldready/mcp_client.py` |
| Real protocol/tool integration | `scripts/check_mcp.py` |
| Browser -> real MCP path | `scripts/check_web.py` |
| Rich M1 MCP/web/export/restart path | `scripts/check_m1_integration.py` |
| Simulated Alexa+ browser source | `src/fieldready/web_app.py`, `src/fieldready/web_assets/` |
| Maintainer-supplied M1 proof | `docs/m1-verification.md` |
| Video technology proof | `docs/demo-script.md` |

Verified maintainer evidence reports negotiated MCP protocol **2026-07-28**, which is later
than the required minimum version.

## Text description

### Submission need

Explain what the project does and how it works.

### FieldReady evidence

Ready-to-paste material:

- `docs/devpost-submission.md`

Supporting detail:

- `README.md`
- `docs/architecture.md`
- `docs/rulesets.md`
- `docs/model-evaluation.md`

## GitHub repository

### Submission need

Repository must contain source code, assets and run instructions and be public with an
open-source licence or shared privately with required reviewers.

### FieldReady evidence

- public repository target: `buriro-ezekia/fieldready-local`;
- Apache-2.0: `LICENSE`;
- setup/run instructions: `README.md`, `docs/setup.md`;
- source: `src/fieldready/`;
- synthetic assets: `src/fieldready/data/`, `src/fieldready/rulesets/`;
- reproducibility snapshot: `requirements.lock.txt`, `docs/environment-lock.json`.

Final repository hygiene:

- `scripts/check_submission.py`

## Demo video

### Submission need

Public YouTube or Vimeo video, English, under three minutes. Lead with the strongest
material because judges are not required to watch beyond the limit.

### FieldReady evidence

- target script: `docs/demo-script.md`;
- target duration: approximately 2:35;
- built-in browser demo path:
  1. Field-survey demo;
  2. Review next priority;
  3. Explain with local model;
  4. Confirm one human decision;
  5. Export review package.

Public demo URL: https://youtu.be/DfNdp4d5lhs

## Product feedback

### Submission need

Describe what was used, what worked well, what needs improvement, onboarding experience and
whether the developer would build with it again.

### FieldReady evidence

Ready-to-paste Alexa+/MCP feedback:

- `docs/devpost-submission.md#product-feedback--alexa--mcp-path`

It describes:

- using the self-hosted MCP route;
- benefits of the tool boundary and structured calls;
- onboarding gaps around conformance/security/video proof;
- willingness to build with MCP again.

## Track and mini challenge

### Current primary track

**Alexa+**

### Mini challenge

**Open Source**

FieldReady Local enters the Open Source Mini Challenge alongside the Alexa+ primary track.

Required Open Source evidence:

- contribution URL: https://github.com/buriro-ezekia/fieldready-local/pull/5
- project repository URL: https://github.com/buriro-ezekia/fieldready-local
- GitHub username: `buriro-ezekia`
- contribution description: `docs/devpost-submission.md#open-source-contribution-description`

AWS Builder Mini Challenge: **No**. The demonstrated solution does not use a qualifying AWS
runtime integration.

## Pre-existing work disclosure

The maintainer confirmed the disclosure in `docs/devpost-submission.md`: FieldReady Local
was created during the hackathon window; only basic repository scaffolding/documentation
preceded the working implementation.

## Optional feature requests

Three evidence-backed candidates are ready in `docs/devpost-submission.md`:

1. official local MCP conformance checker — Important;
2. simulated Alexa+ reference shell — Important;
3. submission readiness checklist — Nice-to-have.

## Optional friction logs

Three logs are prepared in `docs/devpost-submission.md`:

1. proving a real MCP integration;
2. secure localhost simulation;
3. knowing what to show for the simulated Alexa+ route.

These logs are based on actual development work and should not be replaced with invented
friction.

# Judging criteria map

## Tech Implementation

### What judges assess

How well the project is built and how effectively it uses the required technology.

### FieldReady proof

- real self-hosted MCP server;
- Streamable HTTP;
- exact three-tool bounded surface;
- real MCP/browser integration tests;
- SQLite restart persistence;
- versioned ruleset binding;
- report manifest hashes;
- explicit offline proof;
- clean-install/dependency evidence;
- no direct validation fallback when MCP is unavailable.

Best video moment:

> Show the live MCP protocol/tool-count badge in the browser header, then start the
> field-survey workflow. A terminal shot is optional rather than required.

## Design

### What judges assess

Whether the product experience is complete, coherent and intuitive.

### FieldReady proof

- supervisor-oriented overview;
- severity/category summary;
- priority-review action;
- evidence and verification guidance;
- clear separation of AI and human authority;
- explicit review confirmation;
- local export;
- screenshot-safe status messages;
- responsive local browser UI.

Best video moment:

> Review next priority -> evidence panel -> explicit human confirmation.

## Potential Impact

### What judges assess

Whether the project makes a credible case for a real customer need and could serve users
beyond the hackathon.

### FieldReady case

Target users:

- survey supervisors;
- field research teams;
- monitoring/evaluation programmes;
- local data-collection operations.

Specific need:

- catch completeness/consistency/field-quality issues before downstream cleaning;
- support limited-connectivity environments;
- retain auditable human decisions;
- avoid making model-generated prose the source of truth.

Avoid unsupported market-size or adoption claims.

## Quality of the Idea

### What judges assess

Creativity and understanding of the developer ecosystem/end-user need.

### FieldReady differentiation

The core design idea is not merely "AI checks CSVs." It is the boundary:

**deterministic rules own facts -> MCP exposes bounded evidence operations -> local AI only
interprets review focus -> human explicitly owns the decision -> export preserves an audit
trail.**

The development history strengthens this design rationale because measured model failures
directly caused the authority boundary to become stricter.

# Final gate

Before submission:

    .\.venv\Scripts\python.exe scripts/check_submission.py

Do not submit while the audit reports unresolved confirmation markers or a repository-safety
blocker.
