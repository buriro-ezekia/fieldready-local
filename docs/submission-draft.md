# Submission draft — FieldReady Local

> Working draft for the Amazon Developer Hackathon submission. Keep claims aligned with
> verified repository evidence. Replace every TODO with genuine information before submitting.

## Project name

**FieldReady Local**

## One-line pitch

A local survey-quality review assistant that catches data problems before they travel
downstream, explains evidence without letting AI invent facts, keeps supervisors in control,
and exports an audit-ready review package.

## Track

**Alexa+ — simulated Alexa+ experience with a real local MCP backend.**

Do not describe the project as a live Alexa+ connection or an Amazon-certified application.

## What it does

FieldReady Local helps a field supervisor inspect survey-quality problems on the same
computer where the data is being reviewed.

A synthetic survey batch is validated against a versioned ruleset. Findings are presented
with the record, rule, severity, observed value, expected value, deterministic explanation
and verification guidance. The supervisor can review each finding, record a reason and
explicitly confirm the decision without modifying the source CSV.

An optional local language model can interpret what aspect of the review question the user
is asking about, but it does not control scope, write factual evidence or save decisions.
Python decides scope and renders the factual explanation from verified rule evidence.

The reviewed run can be exported locally as:

- a Markdown supervisor summary;
- findings CSV;
- review-history CSV;
- integrity manifest.

The raw source CSV is deliberately excluded from the review package.

## Why it matters

Survey teams can lose time and trust when completeness, consistency or field-quality
problems are discovered only after data has moved to later cleaning and analysis stages.
Connectivity can also be unreliable or costly in field settings.

FieldReady Local demonstrates a workflow in which validation, evidence review, AI assistance,
human approval and report generation can remain local. No hosted database or paid inference
API is required for the demonstrated workflow.

## Rich demonstration

The packaged `field-survey-v1.0.0` synthetic fixture contains:

- 14 fictional records;
- 17 findings;
- 13 affected records;
- 3 critical findings;
- 9 high findings;
- 5 medium findings;
- 80 evaluable rule applications;
- 5 not-evaluable rule applications.

The checks cover completeness, uniqueness, validity, household consistency, conditional
requirements, interview-duration plausibility and GPS accuracy.

## How it was built

### Deterministic validation

Python owns the validation logic. Versioned, package-owned rulesets define supported field
types and a deliberately small set of auditable operators:

- unique;
- sum_equals;
- less_equal;
- between;
- conditional_required.

A rule whose prerequisites are invalid or missing is recorded as not evaluable rather than
being silently treated as a pass.

### MCP layer

FieldReady exposes an official local MCP server over Streamable HTTP.

The tool surface is intentionally limited to:

- `validate_batch`;
- `list_findings`;
- `get_review_summary`.

There is no model-facing review-write, export, shell, arbitrary filesystem, SQL or network
fetch tool.

### Human review

Review state is stored separately in SQLite. Saving a decision requires:

- a permitted review status;
- a stated reason;
- the expected revision;
- a unique request ID;
- explicit confirmation.

The source CSV is never edited by a review action.

### Local AI

The demonstrated model is `qwen2.5:1.5b` through a dedicated local Ollama service.

Measured failures during development changed the architecture:

1. free-form model prose introduced unsupported claims;
2. a raw binary scope classifier achieved only 50% accuracy on a broader test;
3. a first hybrid still rejected legitimate review questions.

The final design therefore makes scope deterministic in Python. The local model performs
only a non-critical review-focus classification. Python renders the factual response from
stored evidence.

### Local reporting

The review package contains four generated files:

- `summary.md`;
- `findings.csv`;
- `review_history.csv`;
- `manifest.json`.

The manifest records SHA-256 hashes for the report/evidence files. The raw imported CSV is
not copied into the package.

## Verified evidence

Verified Windows evidence includes:

- 115 passing tests for the M1 branch;
- MCP protocol 2026-07-28;
- M0 compatibility MCP/restart pass;
- M0 web -> MCP -> SQLite/restart pass;
- M1 real MCP -> web -> export -> restart pass;
- exact M1 14 / 17 / 13 answer key;
- one explicit confirmed review persisted after restart;
- four-file review package with source CSV excluded;
- manual browser rendering of the richer field-survey workflow;
- successful manual local export.

Earlier release-hardening also demonstrated:

- an exact-version Windows runtime snapshot;
- clean installation into a fresh virtual environment;
- explicit network-disabled full-stack operation;
- real local Ollama inference.

Keep branch/head-specific evidence current if the final submission branch changes.

## What was challenging

### Keeping AI useful without making it authoritative

The first local-model design could generate plausible but unsupported explanations. Later
binary classification tests also showed that a small model could be unreliable at deciding
scope. The architecture was changed so deterministic code owns scope and facts while AI has
a bounded advisory role.

### Preserving auditability

The project had to distinguish source evidence, validation findings, review decisions and
AI assistance. The final design keeps these layers separate and preserves explicit review
history rather than modifying imported records.

### Making offline claims measurable

The project does not treat “runs on localhost” as proof of offline operation. The explicit
offline gate first confirms that external probes are unreachable, then exercises the local
MCP, web, SQLite and local-model workflow.

## Accomplishments

- Kept the MCP tool surface small and inspectable.
- Preserved the original source data while maintaining review history.
- Built a versioned rule engine with explicit not-evaluable checks.
- Added a richer synthetic field-survey demonstration.
- Demonstrated real local MCP/web/restart persistence.
- Demonstrated local report export with integrity hashes.
- Measured model failures and redesigned the architecture instead of hiding the failures.
- Kept the demonstrated stack free of paid hosted services.

## What is next

Possible post-hackathon work:

- configurable reviewed ruleset authoring with strong schema validation and approval;
- richer batch-level diagnostics and trend reporting;
- support for more survey questionnaire structures;
- role/access controls for multi-user environments;
- encrypted local storage and production privacy/security review;
- field-device packaging and deployment;
- interoperability with common survey-data workflows.

These are future directions, not current capabilities.

## Product feedback

**TODO — replace with genuine feedback from actual testers or reviewers.**

Suggested structure:

- Who tested it?
- What task did they attempt?
- What was confusing or valuable?
- What changed in the product because of that feedback?

Do not invent quotes or user counts.

## Friction / development log

**TODO — choose genuine examples from the repository history.**

Evidence-backed candidates include:

- GitHub Actions budget limitations led to a local-first verification workflow.
- Windows CRLF versus LF hashing exposed a reproducibility issue and led to canonical
  cross-platform lock hashing.
- Windows 8.3 short-path versus long-path aliases exposed raw path-string comparison bugs
  and led to filesystem-identity checks.
- Free-form local-model explanation produced unsupported speculation.
- Raw binary model scope benchmark failed at 50% accuracy.
- First hybrid routing achieved perfect routing but still rejected legitimate review
  questions, leading to deterministic scope ownership.

## Pre-existing work disclosure

**TODO — confirm exact disclosure before submission.**

State clearly which parts, if any, existed before the hackathon and which were created or
substantially developed during the hackathon. Do not infer this from commit dates alone.

## Demo video

Use [demo-script.md](demo-script.md).

Target: approximately 2 minutes 35 seconds, always below three minutes.

## Repository

Public repository:

`buriro-ezekia/fieldready-local`

Before submission, ensure the final public branch contains:

- source code;
- Apache-2.0 licence;
- setup/run instructions;
- synthetic demo assets;
- ruleset documentation;
- verification evidence;
- demo script;
- no tokens, databases, raw logs, real respondent data or model weights.
