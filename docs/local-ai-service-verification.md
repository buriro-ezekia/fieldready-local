# Reusable local AI browser verification — 1 October 2026

## Scope

This record documents maintainer-supplied Windows evidence after pull request #7
(`Integrate reusable local AI service gateway`) was merged into `main`.

It records a real browser -> FieldReady -> reusable local AI service -> Ollama interaction.
It is distinct from unit-test, MCP, offline and clean-install evidence.

## Runtime path observed

The maintainer started FieldReady with the reusable local AI service already running and
reported the launcher status:

```text
AI: qwen2.5:3b via reusable service 127.0.0.1:8082
```

The browser then displayed:

```text
Configured local model: qwen2.5:3b.
Scope remains deterministic; AI focus is advisory.
```

This establishes that the browser session used the shared loopback service mode rather than
the dedicated Ollama launcher path.

## Browser explanation observation

For the selected richer field-survey finding, the supervisor asked:

> Why is this record flagged, and what should I verify?

The browser displayed the selected evidence as:

- rule: `household.component_total`;
- record ordinal: **2**;
- observed `household_size`: **5**;
- expected component total: **4**;
- verification guidance: check the source component values and the reported total before
  deciding.

The browser also reported:

- model: `qwen2.5:3b`;
- review focus: `combined`;
- elapsed time: **18.42 seconds**;
- evidence reference ending in `:1 / household.component_total`;
- **no review decision was saved**.

The displayed notice stated that scope was decided deterministically, local AI classified
only the review focus, and factual wording was assembled from verified evidence.

## Routing source

In the merged adapter implementation, successful reusable-service inference is labelled:

```text
local_ai_service_focus
```

This routing-source label is implementation metadata. The supplied screenshot shows the
corresponding user-facing service/model/focus result, but does not separately render the
literal `routing_source` field.

## What this establishes

The following Windows/browser path is now demonstrated for the richer field-survey workflow:

**browser -> real MCP-backed finding evidence -> deterministic scope guard -> reusable local
AI service on 127.0.0.1:8082 -> qwen2.5:3b review-focus classification -> deterministic
grounded explanation -> no AI-written review decision**

This closes the earlier M1 visual/manual evidence gap for browser local-model explanation.

## What this does not establish

This observation does not replace separate evidence for:

- the full regression suite;
- the explicit external-network-disabled gate;
- clean-install/package verification;
- broader focus-classification accuracy;
- repeated latency benchmarking;
- browser rendering while external networking is disabled.

Those remain separate verification categories and should be reported only from their own
executions.

## Evidence-handling boundary

The browser screenshot supplied for this observation did not expose the private session
token. The repository records the observed facts only; no local database, model weight,
private session URL, respondent data or raw runtime log is committed.
