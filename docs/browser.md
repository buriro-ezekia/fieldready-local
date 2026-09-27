# Browser review workflow and local explanations

## Status and evidence (27 September 2026)

The maintainer supplied successful Windows results for the previous foundation:
41 core tests passed (2.682 seconds), real MCP protocol **2026-07-28** negotiated,
6 findings returned, and restart persistence preserved 1 confirmed / 5 open findings.
This is maintainer-reported execution, not a rerun inside the implementation environment.

This contribution adds a browser surface, real SDK client, owned-service launcher,
an optional local Ollama explanation connector, and 38 additional unit tests.
In the implementation environment (Linux, Python 3.13.5):

- 38 new tests passed. These use explicitly labelled MCP/model stubs.
- Real web HTTP plus SQLite smoke checks passed with a **stub MCP gateway**:
  authentication, validation route, findings, explicit confirmation, idempotent replay,
  and state after restarting the web server.
- JavaScript syntax checking (`node --check`) and Python source compilation passed.
- Chromium navigation was blocked by the environment's administrator policy.
  No browser rendering or browser interaction pass is claimed.
- `check_web.py` returned exit 2 because `mcp` and `httpx2` are unavailable here.
  The new real web-to-MCP integration must run on the maintainer's installed environment.
- No actual model inference or combined 79-test run was performed here. Re-run the full
  suite on the complete checkout. Existing rules/storage files are unchanged; their
  local test copies were checked against the repository Git blob hashes.

**M0 remains open.** Do not confuse unit/HTTP tests with actual browser rendering,
real SDK execution in the new web path, model quality, or a complete offline evaluation.

## Update and check on Windows

Run from the existing repository root. Do not clone another copy.

```powershell
git switch feat/mcp-validation-slice
git pull --ff-only origin feat/mcp-validation-slice
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install -e ".[mcp]"
& $py -m pip check
& $py scripts/check_local.py --integration
& $py scripts/check_web.py
```

Stop at the first failed command. Do not force-reset or overwrite local changes.
The web check uses its own temporary database, leaving existing review runs untouched.
Its success message is:

```text
WEB HTTP -> MCP -> SQLITE + RESTART: PASS (browser rendering and local inference NOT tested)
```

## Open the browser interface

```powershell
.\.venv\Scripts\python.exe scripts/run_web.py
```

Open the full `http://127.0.0.1:8501/#token=...` session link printed by the launcher.
The fragment contains a random credential; keep it private and do not commit it.
JavaScript stores it in session storage and removes it from the address bar. No token
is embedded in repository assets. Reloading a tab retains its token; restarting the
launcher requires opening its new session link.

The launcher owns the MCP child and stops it when you press Ctrl+C normally. If a
port is already occupied, it refuses to reuse or kill that service. `--web-port` and
`--mcp-port` can select different free local ports. Do not terminate the process forcibly
unless necessary: on Windows, forcibly killing a parent may leave a child running.

Create a **New synthetic review**. Confirm the cards show 8 records, 6 findings and
6 affected records. Select the component-total finding; inspect observed 5 versus
expected 4. Enter a reason, tick the confirmation box and save. Unresolved findings
should become 5. Refresh or restart, select the saved review, and check the decision.
A new synthetic review creates a new run: it does not reopen or replace the old one.
The earlier MCP check used a temporary database, so its test run is not a saved UI run.

Imports must use the same fictional four-column schema and stay within 1 MiB / 2,000
records. The UI lists the latest 100 runs and paginates findings in pages of 50.
Only the canonical `127.0.0.1` session link is accepted by the browser guard.

## Why this interface is not Streamlit

The initial plan proposed Streamlit. This slice instead uses small HTML/CSS/JavaScript
assets with a Python ASGI application, served by the Uvicorn dependency already needed
for MCP. It adds no UI-framework package, CDN, external font or build tool. This is a
local prototype, not a production web service. A more complex UI can be reconsidered later.

Validation and evidence reads go through `MCPGateway` over Streamable HTTP. Importing
bytes, listing saved runs and explicit human review writes remain on the trusted web
control surface. The original MCP tool set remains unchanged: there is no review-write,
arbitrary filesystem, SQL or shell tool. Source records are not modified.

All API data requires a random bearer credential. Host/Origin checks, duplicate-header
rejection, body limits, no-store responses and restrictive content-security policy are
applied. Untrusted values use DOM `textContent`, never `innerHTML`. Review confirmation
is unchecked after changing the reason, outcome or selected finding. Existing SQLite
revision and request-id controls protect stale/replayed decisions. This is not a
production security audit and does not protect against malware running as the same user.

## Optional real local-model connection

First complete the browser workflow without AI. The default explicitly shows **AI disabled**.
To inspect already installed models:

```powershell
ollama list
```

Then stop the launcher normally and restart with an exact installed local name:

```powershell
.\.venv\Scripts\python.exe scripts/run_web.py --model "qwen2.5:1.5b"
```

The launcher starts its own `ollama serve` on 127.0.0.1:11435 with
`OLLAMA_NO_CLOUD=1`. It does not reuse the normal Ollama server, download a model,
or fall back to cloud inference.

### Grounding boundary

The model does **not** generate factual review prose. It only classifies the supervisor's
question as `in_scope` or `out_of_scope` using a constrained JSON schema. Python then
renders the explanation from the verified finding fields. The model never receives a
review-write tool, source CSV, record identifier, supervisor reason, shell, SQL or network
tool.

For an in-scope question, the displayed explanation is assembled from the selected
finding's rule identifier, record ordinal, field, observed value and expected value.
For an out-of-scope question, Python returns a fixed scope message. This prevents model
speculation from entering the factual review surface.

The first real qwen2.5:1.5b run motivated this design: free-form model prose introduced
unsupported statements about survey design, respondents, sampling bias and data-entry
systems. The current architecture removes that failure class instead of trying to maintain
an expanding keyword blacklist.

The UI reports the model name, timing, evidence reference and a notice that local AI
classified the question while the factual wording came from verified evidence. Generation
cannot write a decision.

See [model evaluation](model-evaluation.md) for the real-inference acceptance gate.

Official references: [Ollama local-only configuration](https://docs.ollama.com/faq),
[chat API](https://docs.ollama.com/api/chat), and
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Cost and repository boundaries

No GitHub Actions workflow or run is introduced, and no paid deployment, hosted database,
external inference API or billing change is required. This excludes existing hardware,
electricity and connectivity. Apache-2.0 is preserved. Do not commit databases, tokens,
real survey records or model weights. A tested dependency lockfile is still pending.
