# Devpost submission package — FieldReady Local

This file is structured for direct transfer into the Build, Ship, Shape: Amazon Developer
Hackathon submission form. Claims are limited to repository and maintainer-supplied evidence.

Three items remain intentionally unresolved because they require maintainer confirmation:

- REQUIRES_CONFIRMATION_VIDEO_URL
- REQUIRES_CONFIRMATION_MINI_CHALLENGE
- REQUIRES_CONFIRMATION_PRE_EXISTING_WORK

Do not remove those markers until the corresponding answer is final.

## Project name

**FieldReady Local**

## Tagline

**Catch survey-quality problems locally, explain the evidence, keep supervisors in control.**

## Primary track

**Alexa+**

Submission route: **simulated Alexa+ web experience backed by a real self-hosted MCP
server using Streamable HTTP.**

FieldReady Local does not claim a live Alexa+ connection or Amazon certification.

## Mini challenge

**REQUIRES_CONFIRMATION_MINI_CHALLENGE**

Current candidate:

- **Open Source**, if the maintainer confirms entry and the project satisfies the
  mini-challenge disclosure fields at submission time.

Do not claim the AWS Builder mini challenge: the demonstrated stack intentionally avoids
AWS runtime services and paid cloud dependencies.

## Public repository

**https://github.com/buriro-ezekia/fieldready-local**

Licence: **Apache-2.0**

## Demo video

**REQUIRES_CONFIRMATION_VIDEO_URL**

Requirements for the final link:

- public YouTube or Vimeo;
- English;
- under three minutes;
- no private localhost session token visible;
- no real respondent data;
- no unlicensed music or third-party footage.

Use `docs/demo-script.md` for the current 2:35 target script.

## Short description

FieldReady Local is a local-first survey-quality review assistant for field supervisors.
It validates a survey batch against versioned deterministic rules, surfaces exact evidence,
lets an optional local AI interpret the review focus without inventing factual findings,
requires explicit human approval for decisions, and exports an audit-ready review package
without modifying or copying the raw source CSV.

The hackathon demonstration is a simulated Alexa+ web experience backed by a real local MCP
server over Streamable HTTP.

## Full project description

Field teams can discover missing values, inconsistent household totals, duplicate
identifiers, implausible interview durations or poor GPS quality only after data has already
moved downstream. FieldReady Local moves that review step closer to the point of collection
without requiring a hosted database or paid inference API.

A synthetic survey batch is imported against a package-owned, versioned ruleset. Python
performs deterministic validation and records each finding with its record ordinal, rule,
category, severity, field, observed value, expected value, explanation and verification
guidance. If prerequisites are missing or invalid, the affected rule application is recorded
as **not evaluable** rather than silently counted as a pass.

The richer `field-survey-v1.0.0` demonstration contains 14 fictional records. Its fixed
answer key is:

- 17 findings;
- 13 affected records;
- 3 critical findings;
- 9 high findings;
- 5 medium findings;
- 80 evaluable rule applications;
- 5 not-evaluable rule applications.

A supervisor reviews findings in the browser, records a reason and explicitly confirms the
exact outcome. Review state is stored separately in SQLite; the original source CSV is not
edited. Revision and request-ID checks prevent stale or replayed decisions.

The optional local AI runs through Ollama. It has a deliberately bounded role. Python decides
whether a question is in scope. Only accepted review questions reach the model, which
classifies a non-critical review focus such as **reason**, **verification**, **evidence** or
**review guidance**. Python then renders the factual explanation from verified rule evidence.
The model receives no review-write tool and cannot save decisions.

The reviewed run can be exported locally as:

- `summary.md`;
- `findings.csv`;
- `review_history.csv`;
- `manifest.json`.

The manifest includes SHA-256 hashes for the generated evidence/report files. The raw source
CSV is deliberately excluded.

## How it works

### 1. Versioned validation

FieldReady binds each imported batch to a packaged ruleset. The richer demonstration covers:

- completeness;
- uniqueness;
- category validity;
- numeric ranges;
- household component totals;
- children-under-five consistency;
- conditional required fields;
- interview-duration plausibility;
- GPS-accuracy quality.

### 2. Real MCP backend

FieldReady runs a self-hosted MCP server over Streamable HTTP.

The exposed tool surface is intentionally limited to:

- `validate_batch`;
- `list_findings`;
- `get_review_summary`.

There is no MCP review-write, report-export, shell, SQL, arbitrary-filesystem or network-fetch
tool.

### 3. Human-controlled review

The browser obtains validation/evidence through MCP. A separate trusted local control surface
handles explicit review decisions.

A write requires:

- an allowed review status;
- a stated reason;
- the expected revision;
- a unique request ID;
- explicit confirmation.

### 4. Bounded local AI

The local model is not the source of truth. Model failures measured during development drove
the final architecture:

- free-form explanation introduced unsupported factual speculation;
- the first raw binary scope benchmark achieved 50% accuracy;
- the first hybrid achieved perfect routing but still denied legitimate review questions.

The final design therefore makes scope and factual wording deterministic. The local model
only performs advisory review-focus classification.

### 5. Audit-ready local export

The supervisor can export a four-file review package. The browser writes only to the
application-controlled local export directory, and the source CSV is not copied into the
package.

## Technology used

- Python 3.14.6 in the verified Windows environment;
- official MCP Python SDK v2;
- MCP Streamable HTTP;
- Uvicorn;
- SQLite;
- standard-library ASGI/browser control surface;
- HTML/CSS/JavaScript;
- Ollama with local `qwen2.5:1.5b`;
- Apache-2.0 public GitHub repository.

No hosted database, paid deployment service or paid inference API is required for the
demonstrated workflow.

## Verification evidence

Verified maintainer-supplied Windows evidence includes:

- 115 passing M1 tests;
- negotiated MCP protocol **2026-07-28**;
- M0 MCP/restart compatibility pass;
- M0 web -> MCP -> SQLite/restart compatibility pass;
- M1 real MCP -> web -> export -> restart integration pass;
- exact 14 / 17 / 13 richer-demo answer key;
- one explicit confirmed review persisting after restart;
- four-file local review package with raw source excluded;
- manual browser rendering of the richer M1 workflow;
- successful manual local export.

Earlier release-hardening evidence also demonstrated:

- exact-version Windows dependency snapshot;
- clean installation in a fresh virtual environment;
- explicit network-disabled full-stack operation;
- real local Ollama inference.

See:

- `docs/m1-verification.md`;
- `docs/verification.md`;
- `docs/model-evaluation.md`;
- `docs/rulesets.md`.

## What was challenging

### Making AI useful without making it authoritative

The first local-model design could produce plausible but unsupported factual prose. Later
scope-classification tests showed that a small model could also be unreliable at deciding
whether legitimate review questions should be accepted.

Instead of hiding those failures, the project measured them and redesigned the boundary:
deterministic code owns scope and facts; AI has a bounded advisory role.

### Preserving auditability

Validation findings, source evidence, review decisions and AI assistance needed to remain
separate. FieldReady therefore keeps imported source bytes immutable, stores explicit review
history and requires supervisor confirmation for every decision.

### Proving offline behaviour rather than assuming it

Running on localhost is not automatically evidence of offline operation. The explicit offline
gate first confirms external probes are unreachable, then exercises MCP, web, SQLite, local
AI and the confirmed-review path.

## Accomplishments

- Built and exercised a real self-hosted MCP server with a deliberately bounded three-tool
  surface.
- Preserved immutable source data while supporting persisted supervisor decisions.
- Added versioned survey-quality rules with explicit not-evaluable accounting.
- Built a richer field-survey demonstration with a fixed answer key.
- Demonstrated real MCP/web/restart persistence.
- Demonstrated local export with integrity hashes and raw-source exclusion.
- Measured AI failure modes and redesigned the architecture around evidence rather than
  model confidence.
- Kept the demonstrated system free of paid hosted services.

## Product feedback — Alexa+ / MCP path

### What I used it for

I used the Alexa+ hackathon's self-hosted MCP route as the integration target for a simulated
Alexa+ survey-review experience. FieldReady exposes validation and evidence through a local
MCP server over Streamable HTTP and consumes those tools from the browser workflow.

### What worked well

The MCP tool model encouraged a useful separation between deterministic domain operations and
the user interface. Once the tool surface was deliberately reduced to validation, finding
retrieval and summary retrieval, it became straightforward to reason about what an agent or
simulated Alexa+ experience could and could not do.

Protocol negotiation and structured tool responses also made it possible to build explicit
integration checks instead of treating an SDK import as proof that the MCP path worked.

### What needs work

The main onboarding gap was the lack of a single end-to-end conformance path for a simulated
Alexa+ web experience using self-hosted MCP. I wanted one reference flow that covered:

- minimum acceptable Streamable HTTP server setup;
- localhost authentication/origin guidance;
- exact protocol/tool verification;
- what a simulated experience should visibly demonstrate in the final video;
- how judges distinguish a real MCP call from a README-only integration.

I built custom MCP, restart and web-to-MCP checks to close that gap locally.

### How onboarding felt

The high-level track choice was understandable, but moving from "build an MCP server" to a
submission-grade, securely bounded, testable local integration required more interpretation
than expected.

### Would I build with it again?

**Yes.** The tool boundary maps well to applications where an assistant should retrieve or
trigger narrowly defined operations without inheriting arbitrary filesystem, database or
review-write authority.

## Feature requests

### 1. Official local MCP conformance checker — **Important**

A small official command-line validator could connect to a self-hosted MCP endpoint and
report:

- negotiated protocol;
- transport;
- exposed tools;
- structured-output compatibility;
- common auth/origin issues.

Why it matters: it would reduce the gap between "the SDK imports" and "the required technology
is actually working end to end."

### 2. Simulated Alexa+ reference shell — **Important**

Provide one minimal web simulation that calls a self-hosted MCP server and clearly marks the
boundary between simulation and live Alexa+.

Why it matters: developers could focus on product behaviour while still following a reference
interaction and security pattern.

### 3. Submission readiness checklist — **Nice-to-have**

Provide a track-specific pre-submission validator/checklist for repository, demo and video
requirements.

Why it matters: requirements such as showing the required technology in action are important
but easy to scatter across implementation and recording tasks.

## Friction logs

### Friction log 1 — proving a real MCP integration

**Task attempted:** verify that the project truly satisfied the MCP requirement rather than
merely importing an SDK.

**Steps taken:** built the server, launched it locally, negotiated the protocol with a real
client, listed tools, invoked validation, restarted the service and checked persisted review
state.

**Expected:** an obvious official conformance check that would distinguish a valid
Streamable HTTP implementation from an adapter that only looked correct in source code.

**Actual:** I created a dedicated real-HTTP integration harness and kept core unit tests
separate from MCP evidence.

**Severity:** Important.

**Workaround:** `scripts/check_mcp.py`, `scripts/check_web.py` and the richer
`scripts/check_m1_integration.py`.

**Actionable suggestion:** ship an official MCP track validator that reports protocol,
transport, exposed tools and a sample structured call.

### Friction log 2 — secure localhost simulation

**Task attempted:** expose a browser simulation and MCP server locally without turning
localhost into an unrestricted trusted boundary.

**Steps taken:** added bearer credentials, exact Host/Origin checks, duplicate-header
rejection, request limits, no-store responses and a canonical `127.0.0.1` session URL.

**Expected:** reference security guidance for hackathon-style localhost MCP simulations.

**Actual:** the security boundary had to be assembled and tested from lower-level pieces.

**Severity:** Important.

**Workaround:** a dedicated local guard and authenticated browser session with the credential
removed from the visible address bar after startup.

**Actionable suggestion:** publish a secure-localhost sample for simulated Alexa+ + MCP
experiences, including Host/Origin/auth guidance.

### Friction log 3 — knowing what to show for the simulated Alexa+ route

**Task attempted:** design a sub-three-minute demo that proves the required technology is
actually being used while accurately labelling the experience as a simulation.

**Steps taken:** separated unit, MCP, web, browser and model evidence; created an explicit
recording script; added visible "Simulated Alexa+ experience" language in the UI.

**Expected:** a concise checklist showing the minimum proof judges expect for a simulated
Alexa+ web experience backed by MCP.

**Actual:** I translated the written requirements into an internal recording and evidence
checklist.

**Severity:** Nice-to-have.

**Workaround:** `docs/demo-script.md` and the built-in 2-minute demo path.

**Actionable suggestion:** provide a sample submission video/storyboard for the simulated
Alexa+ path showing exactly how to demonstrate the MCP call without implying a live Alexa+
connection.

## Pre-existing work disclosure

**REQUIRES_CONFIRMATION_PRE_EXISTING_WORK**

Choose and edit one of these before submission.

### Option A — project started during the hackathon

> FieldReady Local was created during the hackathon submission window. No pre-existing
> FieldReady Local implementation was reused. The repository, MCP integration, deterministic
> validation/review workflow, local AI boundary, versioned rulesets, reporting and browser
> experience were developed for this submission.

Use this only if completely accurate.

### Option B — related work existed before the hackathon

> Before the hackathon, I had [DESCRIBE THE PRE-EXISTING IDEA/CODE/COMPONENT]. During the
> submission window I built or substantially changed [LIST THE SPECIFIC FIELDREADY LOCAL
> COMPONENTS CREATED DURING THE HACKATHON].

Replace every bracketed field with the exact truth.

## Screenshot captions

### Screenshot 1 — Supervisor overview

**FieldReady Local validates a versioned synthetic field-survey batch locally and gives the
supervisor an evidence-backed queue: 14 records, 17 findings, 13 affected records, with
severity and issue-category summaries.**

### Screenshot 2 — Evidence and human decision

**The supervisor sees the deterministic rule, severity, observed/expected values, why the
record was flagged and what to verify. A decision is saved only after an explicit reason and
confirmation.**

### Screenshot 3 — Bounded local AI

**Python decides scope and owns the factual evidence. The local model only classifies the
review focus; it cannot edit source records or save a review decision.**

### Screenshot 4 — Local report export

**The reviewed run exports a local Markdown summary, findings CSV, review-history CSV and
integrity manifest. The raw source CSV is deliberately excluded.**

## Final pre-submit checklist

- [ ] Confirm participant eligibility under the hackathon rules.
- [ ] Replace REQUIRES_CONFIRMATION_VIDEO_URL.
- [ ] Replace REQUIRES_CONFIRMATION_MINI_CHALLENGE.
- [ ] Replace REQUIRES_CONFIRMATION_PRE_EXISTING_WORK.
- [ ] Video is public, English and under three minutes.
- [ ] Video shows the simulated Alexa+ experience and real MCP-backed workflow in action.
- [ ] Public GitHub repository contains source, assets, instructions and Apache-2.0 licence.
- [ ] Screenshot/video contains no localhost token.
- [ ] Screenshot/video contains no personal Windows filesystem path.
- [ ] No real survey/respondent data appears.
- [ ] Product feedback is pasted into the required feedback field.
- [ ] Track/mini-challenge fields are selected consistently with this document.
- [ ] If entering Open Source, add the required contribution/repository/user/description fields.
- [ ] Pre-existing-work disclosure is accurate.
- [ ] Consider submitting the friction logs for the optional judging bonus.
