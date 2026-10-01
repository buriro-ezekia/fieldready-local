# Reusable local AI service integration

FieldReady Local can use either its existing dedicated Ollama process or an already-running
reusable local AI service. Both modes keep deterministic Python in control of scope, factual
evidence and review decisions.

## Architecture

```text
FieldReady browser
      |
      v
FieldReady web backend
      |
      +--> deterministic scope guard
      |
      +--> reusable local AI service (127.0.0.1:8082)
      |         |
      |         +--> qwen2.5:3b primary
      |         +--> qwen2.5:1.5b fallback
      |
      +--> deterministic grounded explanation
      |
      v
explicit human review decision
```

The model receives only the accepted supervisor question and a fixed focus-classification
instruction. Finding evidence, respondent identifiers and review-write capabilities are not
sent to the model. Python renders the factual explanation from verified rule evidence.

## Start the reusable service

Start the separate local AI service first. In the service directory on Windows:

```powershell
.\run.ps1
```

Verify it:

```powershell
Invoke-RestMethod http://127.0.0.1:8082/health
```

For the current local setup, the expected primary/fallback pair is:

```text
qwen2.5:3b
qwen2.5:1.5b
```

## Start FieldReady through the service

From the FieldReady repository root:

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/run_web.py --ai-service-port 8082 --model "qwen2.5:3b"
```

The `--model` argument is optional in service mode. If omitted, FieldReady uses the primary
model reported by the service:

```powershell
& $py scripts/run_web.py --ai-service-port 8082
```

FieldReady verifies that:

- the gateway is reachable only through the supplied loopback port;
- the gateway reports a loopback Ollama `/api` backend;
- the requested/primary model is installed;
- every model the gateway may select has local, non-remote Ollama metadata;
- any model returned after fallback belongs to that verified local set;
- the structured response contains exactly one supported review focus.

If the service is unavailable or returns an invalid response, FieldReady returns a local
service error. It does not add a cloud fallback.

## Existing dedicated-Ollama mode

The original verified mode remains unchanged:

```powershell
& $py scripts/run_web.py --model "qwen2.5:1.5b"
```

In this mode FieldReady starts its own Ollama service on the dedicated loopback port and sets
`OLLAMA_NO_CLOUD=1`.

Use the dedicated mode for the existing explicit offline/submission verification path. Use
the reusable-service mode when several local applications should share one AI gateway.

## Responsibility boundary

The AI layer may classify only one non-critical review focus:

- `reason`;
- `verification`;
- `evidence`;
- `review_guidance`;
- `combined`.

It does not calculate findings, change validation results, edit imported data, execute shell
commands or save review decisions.
