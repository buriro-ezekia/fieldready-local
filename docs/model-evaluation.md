# Local model evaluation

## Architecture after the first real-inference failure

FieldReady Local no longer allows the language model to write factual review prose.

The local model performs one bounded task: classify the supervisor's natural-language
question as either `in_scope` or `out_of_scope`. Python then assembles every factual
statement from the deterministic finding evidence already returned by the validation layer.

This separation is deliberate:

- Python owns rule identifiers, record ordinals, observed values and expected values.
- The model never receives tools and cannot save a review decision.
- The model cannot add free-form factual claims to the displayed explanation.
- The browser labels the result as AI-assisted question interpretation plus grounded evidence.
- A failed or unavailable model produces no substitute cloud response.

The first real model target remains `qwen2.5:1.5b`, previously used locally by the
maintainer. This is a test target, not a commitment to the final release.

## Real local-inference gate

Run from the repository root:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/check_model.py --model "qwen2.5:1.5b"
```

The check:

- requires an already installed Ollama executable and exact model name;
- launches a dedicated loopback Ollama service on port 11435;
- sets `OLLAMA_NO_CLOUD=1`;
- performs one real structured intent classification;
- does not download a model;
- does not provide tools to the model;
- does not alter SQLite or a review decision;
- validates the deterministic evidence references returned with the grounded result;
- fails rather than falling back to a hosted model.

A successful run ends with:

```text
LOCAL MODEL + GROUNDED EXPLANATION: PASS (broader intent quality is not yet evaluated)
```

For the fixture question, the model should classify the request as `in_scope`. The displayed
text must then be assembled from the known finding:

- rule: `component_total`;
- record ordinal: 2;
- field: `household_size`;
- observed: 5;
- expected: 4.

This gate establishes real local inference plus deterministic evidence rendering. It does not
establish general intent-classification quality across arbitrary questions.

## Browser test after the gate

After a successful check:

```powershell
& $py scripts/run_web.py --model "qwen2.5:1.5b"
```

Create or reopen a synthetic review, select the component-total finding and ask:

> Why was this finding raised, and what should I verify before confirming it?

The result should state that `household_size` is recorded as 5 while the validated component
total is 4, and direct the supervisor to verify the source component values before deciding.
The model itself does not author those factual statements.

For an unrelated question, the model may classify it as `out_of_scope`; Python then returns
a fixed scope message instead of answering the unrelated request.

## Why the architecture changed

The first real `qwen2.5:1.5b` run completed locally but produced unsupported prose about
survey design, respondents, sampling bias and data-entry systems. Rejecting particular words
would remain brittle. Constraining the model to an intent enum removes that entire class of
failure from the factual review surface.

## If the check fails

Do not download another model automatically and do not enable a cloud endpoint. Preserve the
complete terminal error. The next action depends on whether the failure is model discovery,
Ollama startup, structured intent classification or local runtime behaviour.

A later evaluation should test intent accuracy, latency and memory use across a broader set
of representative supervisor questions.
