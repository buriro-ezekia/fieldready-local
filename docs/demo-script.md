# FieldReady Local — hackathon demo script

Target length: **2 minutes 35 seconds**. Keep the full recording under three minutes.

## Before recording

Use the verified M1 branch plus presentation-polish branch. Start the application with the
installed local model:

    .\.venv\Scripts\python.exe scripts/run_web.py --model "qwen2.5:1.5b"

Open the private localhost session link, then make sure the token has disappeared from the
address bar before recording.

Use only the built-in synthetic **Field-survey demo**. Do not display a real survey file,
database, token, terminal secret or respondent record.

Keep the terminal available for one short MCP proof if needed, but make the browser the
primary visual.

## Recording sequence

### 0:00–0:18 — Problem and product

**On screen:** FieldReady Local home view.

**Narration:**

> Field teams often discover survey-quality problems only after data has moved downstream.
> FieldReady Local checks a survey batch on the same computer, shows supervisors the exact
> evidence, and keeps every decision human-controlled.

Point briefly to the header trust signals:

- Local-first
- MCP-backed
- Human-approved

Do not describe this as a live Alexa+ integration. The submission is a simulated Alexa+
experience backed by the real local MCP server.

### 0:18–0:38 — Start the richer field-survey demo

Click **Field-survey demo**.

**On screen:** 14 records, 17 findings, 13 affected records.

**Narration:**

> This fictional field batch is bound to a versioned ruleset. Fourteen records produce
> seventeen findings across completeness, validity, consistency, duration, uniqueness and
> GPS-quality checks.

Point to:

- critical 3
- high 9
- medium 5
- 80 evaluable / 5 not evaluable

**Key message:** a failed prerequisite becomes “not evaluable”; it is not silently counted
as a pass.

### 0:38–1:05 — Priority evidence

Click **Review next priority**.

**On screen:** highest-priority unresolved finding and Evidence & decision panel.

**Narration:**

> The queue prioritises unresolved evidence for review. The rule, severity, field,
> observed value, expected value, why it was flagged and what the supervisor should verify
> all come from deterministic Python rules—not from the language model.

Pause long enough for the evidence to be readable.

### 1:05–1:32 — Local AI, bounded role

In the question box use:

> Why is this record flagged, and what should I verify?

Click **Explain with local model**.

**Narration while it runs:**

> The optional local model never receives a review-write tool and does not author the
> factual finding. Python decides whether the question is in scope; the local model only
> classifies the review focus; Python renders the explanation from verified evidence.

When the answer appears, point to:

- model name
- review focus
- evidence reference
- notice that no decision was saved

Do not claim a particular latency before seeing the measured value on screen.

### 1:32–1:58 — Human approval and immutable source

Choose **Confirmed**, enter a short reason such as:

> Checked the synthetic source evidence.

Tick:

> I approve this exact review decision.

Click **Save confirmed decision**.

**Narration:**

> A model cannot make this change. The supervisor must state a reason and explicitly approve
> the exact decision. The original CSV is never edited; review state is stored separately
> with revision and replay protection.

Show unresolved findings decrease by one.

### 1:58–2:20 — Local supervisor export

Click **Export review package**.

**Narration:**

> The supervisor can export an audit-ready local package containing a Markdown summary,
> findings CSV, review-history CSV and integrity manifest.

Point to the screenshot-safe success message, which shows only the relative local `exports/<run-id>/` location.

> The raw source CSV is deliberately excluded.

If useful, briefly show the export folder after recording the main browser flow. Do not spend
time opening all four files in the main demo.

### 2:20–2:35 — Close with architecture and impact

**On screen:** browser summary.

**Narration:**

> FieldReady Local combines deterministic survey-quality rules, a bounded MCP interface,
> optional local AI and explicit human review. It works without a hosted database or paid
> inference API, and is designed for teams that need evidence and accountability even when
> connectivity is limited.

End on the FieldReady Local interface.

## Optional five-second MCP proof

If the judges need more explicit technology evidence, briefly show the terminal line:

    MCP ready: protocol 2026-07-28; tools: get_review_summary, list_findings, validate_batch

Do not spend more than five seconds on the terminal. The browser workflow already consumes
those tools through the real MCP gateway.

## Recording checklist

Before submitting the video, verify all of the following:

- duration is below three minutes;
- no private localhost token is visible;
- no real survey/respondent data appears;
- the Field-survey demo is used, not only the legacy household demo;
- 14 / 17 / 13 headline counts are visible;
- severity and rule-evaluation summary are visible;
- one evidence-backed finding is opened;
- local AI is shown only in its bounded review-focus role;
- one explicit human review decision is saved;
- unresolved count decreases;
- export success is shown;
- raw source exclusion is mentioned;
- no live Alexa+ certification or connection is claimed;
- no cloud model or paid hosting claim is implied.

## Screenshot set for the submission page

Capture three clean screenshots in addition to the video:

1. **Supervisor overview** — 14 records / 17 findings / 13 affected records plus severity.
2. **Evidence & human decision** — one critical/high finding with verification guidance.
3. **Export success / local assistant** — show either the grounded local explanation or the
   successful four-file report export.

Do not include the private session token in any screenshot.
