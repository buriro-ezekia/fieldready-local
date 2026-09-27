# Local model evaluation

## First real-inference gate

FieldReady Local uses the language model only to explain deterministic findings. Python remains
the source of validation results and the model cannot save review decisions.

The first real model target is `qwen2.5:1.5b`, which was previously used locally by the
maintainer. This is a test target, not a claim that it will be retained for the final release.

Run from the repository root:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/check_model.py --model "qwen2.5:1.5b"
```

The check:

- requires an already installed Ollama executable and exact model name;
- launches a dedicated loopback Ollama service on port 11435;
- sets `OLLAMA_NO_CLOUD=1`;
- performs one explanation against synthetic evidence;
- does not download a model;
- does not provide tools to the model;
- does not alter SQLite or a review decision;
- fails rather than falling back to a hosted model.

A successful run ends with:

```text
LOCAL MODEL EXPLANATION: PASS (quality beyond this fixture is not yet evaluated)
```

This only establishes that one real local explanation completed and retained the expected
evidence reference. It is not a systematic quality evaluation.

## Browser test after the gate

After a successful check, start the application with the same exact installed name:

```powershell
& $py scripts/run_web.py --model "qwen2.5:1.5b"
```

Create or reopen a synthetic review, select the component-total finding and ask:

> Why was this finding raised, and what should I verify before confirming it?

Compare the generated explanation against the displayed evidence. It should preserve the
rule identifier `component_total`, record ordinal 2, observed value 5 and expected value 4.
It must not claim that the source record has been corrected.

## If the check fails

Do not download another model automatically and do not enable a cloud endpoint. Preserve the
complete terminal error. The next action depends on whether the failure is model discovery,
Ollama startup, local inference, or output-quality validation.

The final model choice will require a broader measured evaluation covering evidence fidelity,
unsupported claims, latency and memory use.
