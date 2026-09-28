# Submission visual assets — capture plan

Use the polished `feat/demo-polish` browser only after its regression checks pass.

Recommended capture size: **1600×900** or another clean 16:9 viewport. Keep browser zoom at
90–100% so the important evidence is readable without showing unnecessary desktop chrome.

Before every screenshot:

- make sure the private `#token=...` fragment is gone from the address bar;
- close bookmarks/favourites bars if they reveal personal information;
- use only the built-in synthetic Field-survey demo;
- do not show terminal secrets, local database paths or real survey data;
- do not show a personal Windows user path;
- keep the "Simulated Alexa+ experience" label visible when possible.

## Screenshot 1 — Supervisor overview

### State

1. Start `Field-survey demo`.
2. Do not select a finding yet.
3. Scroll so the product proposition, supervisor snapshot and four headline metrics are
   visible together.

### Must show

- FieldReady Local branding;
- Local-first / live MCP protocol+tool-count badge / Human-approved;
- 14 records;
- 17 findings;
- 13 affected records;
- severity chips: critical 3 / high 9 / medium 5;
- rule-evaluation line: 80 evaluable / 5 not evaluable;
- issue-category snapshot.

### Caption

> FieldReady Local validates a versioned synthetic field-survey batch locally and gives the
> supervisor an evidence-backed queue: 14 records, 17 findings, 13 affected records, with
> severity and issue-category summaries.

### Filename

`01-supervisor-overview.png`

## Screenshot 2 — Evidence and human control

### State

1. Click **Review next priority**.
2. Keep the selected finding visible in the queue.
3. Make sure the Evidence & decision panel shows:
   - rule;
   - category;
   - severity;
   - observed;
   - expected;
   - why flagged;
   - what to verify.
4. Leave the confirmation box visible.

### Must show

- deterministic evidence;
- a critical or high finding;
- explicit human decision form;
- the statement that source CSV is never edited.

### Caption

> The supervisor sees the deterministic rule, severity, observed/expected values, why the
> record was flagged and what to verify. A decision is saved only after an explicit reason
> and confirmation.

### Filename

`02-evidence-human-decision.png`

## Screenshot 3 — Bounded local AI

### State

1. Keep a finding selected.
2. Ask:
   **Why is this record flagged, and what should I verify?**
3. Wait for the grounded result.
4. Capture the explanation assistant plus enough of the evidence panel to link the answer to
   the selected finding.

### Must show

- grounded deterministic explanation;
- local model name;
- advisory focus;
- evidence reference;
- notice that no review decision was saved.

### Caption

> Python decides scope and owns the factual evidence. The local model only classifies the
> review focus; it cannot edit source records or save a review decision.

### Filename

`03-bounded-local-ai.png`

## Screenshot 4 — Local export proof

### State

1. Save one explicit review decision first.
2. Click **Export review package**.
3. Capture the green success notice plus the headline metrics/supervisor snapshot.

### Expected safe message

The browser should show a repository-neutral relative location similar to:

`Review package exported locally under exports/<run-id>/.`

It must **not** show a personal absolute Windows user-directory path.

### Must show

- export success;
- raw source CSV excluded;
- unresolved count reduced after one reviewed finding.

### Caption

> The reviewed run exports a local Markdown summary, findings CSV, review-history CSV and
> integrity manifest. The raw source CSV is deliberately excluded.

### Filename

`04-local-export.png`

## Video framing

The video should primarily use browser content, not terminal output.

If showing the MCP proof, limit the terminal to approximately five seconds and show only:

`MCP ready: protocol 2026-07-28; tools: get_review_summary, list_findings, validate_batch`

Do not show:

- the private browser token;
- environment variables;
- the full SQLite location;
- Ollama model files;
- personal folders;
- GitHub credentials.

## Selection for Devpost gallery

If only three images are practical, use:

1. Supervisor overview;
2. Evidence and human decision;
3. Bounded local AI.

Keep the export proof in the video.

If four images are supported cleanly, include all four.

## Final visual consistency check

All submission visuals should tell the same story:

**Local validation -> evidence -> bounded AI -> explicit human decision -> local audit export**

Avoid screenshots that show only implementation details or terminal logs without the product
workflow.
