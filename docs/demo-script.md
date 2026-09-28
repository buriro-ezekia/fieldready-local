# FieldReady Local — final YouTube demo script

**Target duration:** 2:30–2:40  
**Hard limit:** under 3:00  
**Format:** browser-first screen recording with English narration  
**Demo data:** built-in synthetic Field-survey demo only

The official hackathon rules require a public YouTube/Vimeo demo under three minutes. For
the Alexa+ simulated-experience path, the video should clearly show the experience working.
The browser itself now shows the negotiated MCP protocol and tool count, so a terminal shot
is optional.

---

## Before recording

1. Pull the latest `feat/demo-polish` branch.
2. Run:

       .\.venv\Scripts\python.exe scripts/run_web.py --model "qwen2.5:1.5b"

3. Open the private local session link.
4. Wait until the `#token=...` fragment disappears from the browser address bar.
5. Use the **Field-survey demo** only.
6. Set browser zoom to about 90–100%.
7. Hide bookmarks/favourites bars and notifications.
8. Do not show real data, terminal secrets, personal paths or credentials.
9. Record at 1080p / 16:9 if practical.
10. Do not use copyrighted music. A clean voice-over with no music is sufficient.

---

# Exact recording sequence and narration

## 0:00–0:16 — Problem + product

### On screen
Start on the polished FieldReady Local browser home view.

Make sure the header shows:

- Local-first
- live MCP protocol/tool-count badge
- Human-approved

### Say

> Field teams often discover survey-quality problems only after the data has already moved
> downstream. FieldReady Local brings that review step closer to collection: it validates
> locally, shows supervisors the evidence, and keeps every decision human-controlled.

### Purpose
Immediately establishes the customer problem and product value.

---

## 0:16–0:30 — Prove the Alexa+/MCP technology

### On screen
Point briefly to the live badge, for example:

> MCP 2026-07-28 · 3 tools

### Say

> This is a simulated Alexa+ experience backed by a real self-hosted MCP server over
> Streamable HTTP. The browser is showing the negotiated MCP protocol and the bounded tool
> surface live.

### Purpose
Proves the required technology inside the product instead of relying on a terminal.

---

## 0:30–0:52 — Start the richer field-survey workflow

### Action
Click **Field-survey demo**.

Wait for the dashboard to populate.

### On screen
Show clearly:

- 14 records
- 17 findings
- 13 affected records
- critical 3
- high 9
- medium 5
- 80 evaluable
- 5 not evaluable

### Say

> This fictional field-survey batch is bound to a versioned ruleset. Fourteen records
> produce seventeen evidence-backed findings across completeness, validity, consistency,
> uniqueness, interview duration and GPS quality. If a rule cannot be evaluated because a
> prerequisite is missing or invalid, FieldReady records that explicitly instead of silently
> treating it as a pass.

### Purpose
Shows product depth and the richer M1 demo immediately.

---

## 0:52–1:17 — Open the highest-priority evidence

### Action
Click **Review next priority**.

### On screen
Keep the selected row and the Evidence & decision panel visible.

Pause briefly on:

- Rule
- Category
- Severity
- Observed
- Expected
- Why flagged
- What to verify

### Say

> The supervisor can jump directly to the highest-priority unresolved finding. The rule,
> severity, observed value, expected value, why it was flagged and what should be verified
> all come from deterministic Python rules — not from the language model.

### Purpose
Makes the evidence/authority boundary obvious.

---

## 1:17–1:47 — Show the bounded local AI

### Action
In the assistant, ask:

> Why is this record flagged, and what should I verify?

Click **Explain with local model**.

### While it runs, say

> The optional local model is deliberately bounded. Python decides whether the question is
> in scope. The model only classifies the review focus, and Python renders the factual
> explanation from verified evidence. The model cannot edit records or save a decision.

### When the answer appears
Point briefly to:

- grounded explanation
- model name
- Focus
- elapsed time
- evidence reference
- notice that no review decision was saved

### Then say

> So AI helps the supervisor understand the review, but it never becomes the source of truth.

### Purpose
This is the strongest differentiating moment in the video.

---

## 1:47–2:10 — Show explicit human control

### Action
In the decision panel:

- select **Confirmed**
- type: `Checked the synthetic source evidence.`
- tick **I approve this exact review decision**
- click **Save confirmed decision**

### On screen
Show unresolved findings decrease by one.

### Say

> A model cannot make this change. The supervisor must state a reason and explicitly approve
> the exact decision. The original CSV is never edited; review state is stored separately
> with revision and replay protection.

### Purpose
Demonstrates trust, auditability and product design.

---

## 2:10–2:27 — Export the audit-ready package

### Action
Click **Export review package**.

### On screen
Show the screenshot-safe success message:

> Review package exported locally under exports/<run-id>/. Raw source CSV was not included.

### Say

> The reviewed run exports a Markdown summary, findings CSV, review-history CSV and integrity
> manifest. The raw source CSV is deliberately excluded.

### Purpose
Shows the supervisor's tangible end product.

---

## 2:27–2:38 — Close with the core idea

### On screen
Return attention to the dashboard / supervisor snapshot.

### Say

> FieldReady Local combines deterministic survey-quality rules, bounded MCP, optional local
> AI and explicit human review in one local-first workflow. The key idea is simple: evidence
> stays authoritative, AI stays bounded, and the human stays in control.

Stop recording.

---

# Total narration

Target spoken duration: approximately **2:20–2:30**, leaving several seconds for UI
response time and natural pauses.

If local inference takes longer than expected, continue speaking the explanation of the AI
boundary while it runs. Do not wait silently for more than a few seconds.

---

# What NOT to show

Do not spend video time on:

- running all unit tests;
- opening source-code files;
- explaining SQLite tables;
- scrolling GitHub commits;
- showing the full dependency lock;
- discussing historical model failures in detail;
- opening all four export files;
- showing a private localhost token;
- showing a personal Windows path;
- showing real survey/respondent data;
- claiming a live Alexa+ connection or Amazon certification.

Those details belong in the repository and written submission.

---

# Optional terminal proof

A terminal shot is no longer necessary because the browser shows live MCP health.

If you still want one, show it for **no more than five seconds** and only show:

    MCP ready: protocol 2026-07-28; tools: get_review_summary, list_findings, validate_batch

Never show environment variables or private tokens.

---

# Final pre-recording checklist

- [ ] Browser is on `feat/demo-polish`.
- [ ] Application launched with `qwen2.5:1.5b`.
- [ ] Session token is no longer visible in the address bar.
- [ ] Live MCP badge is visible.
- [ ] Field-survey demo produces 14 / 17 / 13.
- [ ] Severity shows critical 3 / high 9 / medium 5.
- [ ] Rule evaluation shows 80 evaluable / 5 not evaluable.
- [ ] Review next priority works.
- [ ] Local AI explanation works.
- [ ] Explicit human decision works.
- [ ] Export success is screenshot-safe.
- [ ] No personal path appears.
- [ ] No real data appears.
- [ ] Recording is 1080p/16:9 if practical.
- [ ] English narration is clear.
- [ ] Final video is under 3:00.
- [ ] No copyrighted music/footage is used.

---

# The story judges should remember

**Problem -> live MCP proof -> rich survey findings -> deterministic evidence -> bounded local AI -> explicit human decision -> audit-ready local export.**

And the one-line idea:

> **Evidence stays authoritative, AI stays bounded, and the human stays in control.**
