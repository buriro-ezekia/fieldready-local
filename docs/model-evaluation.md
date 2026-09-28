# Local model evaluation

## Final production architecture

FieldReady Local does **not** allow the language model to decide access to the review
workflow and does **not** allow it to write factual review prose.

The production sequence is:

1. Python applies a deterministic scope guard.
2. Clearly unrelated requests are returned as `out_of_scope` without model inference.
3. Legitimate review questions are accepted deterministically as `in_scope`.
4. Only accepted review questions reach `qwen2.5:1.5b`.
5. The local model classifies a non-critical review focus:
   `reason`, `verification`, `evidence`, `review_guidance`, or `combined`.
6. Python renders the factual explanation from verified finding evidence.
7. The model has no review-write tool and cannot change source data or supervisor decisions.

This architecture separates three concerns:

- **scope/safety**: deterministic Python;
- **natural-language interpretation**: local model, advisory only;
- **facts/actions**: deterministic Python plus explicit human confirmation.

No cloud fallback is permitted.

## Why the architecture changed

Three stages of evidence led to the current design.

### Free-form factual model output

The first real `qwen2.5:1.5b` explanation completed locally but introduced unsupported
claims about survey design, respondents, sampling bias and data-entry systems.

Response: remove factual prose generation from the model entirely.

### Raw binary scope classifier

The first broader benchmark used the model to classify `in_scope` versus
`out_of_scope` directly:

- 32 evaluations;
- 16 correct;
- accuracy **0.50**;
- in-scope recall **1.00**;
- out-of-scope recall **0.00**;
- the model predicted `in_scope` for every question.

Response: add a deterministic scope guard before inference.

### First hybrid router

The next benchmark routed all 32 cases correctly to either the guard or the model, but
still allowed the model to make the final in-scope/out-of-scope decision for review-related
questions:

- 32 evaluations;
- 26 correct;
- accuracy **0.8125**;
- in-scope recall **0.625**;
- out-of-scope recall **1.00**;
- deterministic routing accuracy **1.00**;
- 16 model invocations and 16 guarded requests;
- six legitimate review queries were denied by the model;
- model latency mean **1.856 s**, median **1.39 s**, p95 **7.95 s**.

Response: remove scope authority from the model entirely.

## Single real-model smoke check

Run:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/check_model.py --model "qwen2.5:1.5b"
```

The smoke check uses an unambiguous review question:

> Why was this finding raised?

Expected production behaviour:

- deterministic scope: `in_scope`;
- local model focus: `reason`;
- grounded evidence: `component_total`, record ordinal 2, observed 5, expected 4;
- no decision write;
- no cloud fallback.

A successful run ends with:

```text
LOCAL MODEL FOCUS + GROUNDED EXPLANATION: PASS
```

## Final broader benchmark

The benchmark dataset contains 16 synthetic questions:

- 8 legitimate review questions;
- 8 clearly unrelated questions.

Each in-scope case also has an expected advisory focus label.

Run:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/evaluate_intent.py --model "qwen2.5:1.5b" --repeats 2
```

This produces 32 production-router evaluations and writes:

```text
runtime\intent-eval.json
```

### Hard acceptance criteria

The final router must satisfy all of the following:

- runtime/schema errors: **0**;
- deterministic scope accuracy: **100%**;
- in-scope recall: **100%**;
- out-of-scope recall: **100%**;
- expected routing accuracy: **100%**;
- model invocations: exactly all in-scope evaluations;
- guarded requests: exactly all out-of-scope evaluations.

These criteria are strict because scope is no longer probabilistic.

### Advisory AI-focus criterion

The local model's five-way focus accuracy must be at least **75%** on in-scope
evaluations.

A wrong focus cannot deny the question, change evidence, alter the rendered factual text,
or save a decision. The focus metric therefore measures usefulness rather than safety.

### Latency reporting

The benchmark reports separately:

- model-only latency for in-scope questions;
- end-to-end latency for all requests;
- mean, median, p95, minimum and maximum values.

Out-of-scope requests should be near-instant because the model is not invoked.

There is no fixed latency pass threshold yet; the measured distribution will inform the
final demo decision.

## Browser behaviour

For an accepted review question, the browser shows:

- the deterministic grounded explanation;
- the local model name;
- the advisory focus when available;
- model latency;
- the evidence reference;
- a notice that scope and factual content are not model-controlled.

For an unrelated question, the deterministic guard returns the fixed out-of-scope response
without model inference.

## Evidence boundary

Passing the final benchmark certifies the scope/focus router only. Because production code
changed after earlier clean-install and offline passes, both gates must be rerun once more
on the final branch head before submission evidence is frozen.
