# Release hardening: dependency snapshot and explicit offline proof

This stage turns the verified Windows prototype into reproducible release evidence without
introducing paid hosting, a hosted database, a cloud model API or GitHub Actions.

## 1. Capture the tested dependency environment while still online

Run from the repository root with the existing project virtual environment:

```powershell
$py = ".\.venv\Scripts\python.exe"

& $py scripts/check_local.py
if ($LASTEXITCODE -ne 0) { throw "Local checks failed." }

& $py scripts/write_lock.py
if ($LASTEXITCODE -ne 0) { throw "Environment snapshot failed." }

Get-Content .\requirements.lock.txt
Get-Content .\docs\environment-lock.json
```

The writer does **not** resolve or download packages. It records exact versions already
installed in the virtual environment after `pip check` passes. It refuses to run from the
system interpreter, excludes the FieldReady project itself and rejects non-version-pinned
entries.

It creates:

- `requirements.lock.txt` — exact package versions from the tested environment;
- `docs/environment-lock.json` — Python/platform metadata and the lock-file SHA-256.

This is an exact-version environment snapshot. It is intentionally not described as a
hash-locked wheel supply-chain manifest.

Do not hand-edit either generated file. Review the output before committing it.

## 2. Disable external networking

After the model and all Python dependencies are already installed, disconnect external
network access. On Windows, the clearest evidence is to disconnect Wi-Fi and Ethernet
(or enable an equivalent offline mode) while leaving the computer running.

Localhost remains available when external networking is disconnected, so the MCP, web,
SQLite and Ollama processes can still communicate through 127.0.0.1.

## 3. Run the explicit offline gate

While still disconnected:

```powershell
$py = ".\.venv\Scripts\python.exe"

& $py scripts/check_offline.py --model "qwen2.5:1.5b"
```

The script first probes three external targets. **If any connection succeeds, the test
fails and does not count as offline evidence.** If all probes are unreachable, it then:

1. runs `pip check`;
2. runs the real MCP/restart integration;
3. runs the real web -> MCP -> SQLite integration;
4. starts a dedicated local Ollama service with cloud access disabled;
5. starts the browser backend with the real MCP gateway and local model;
6. validates the synthetic batch;
7. retrieves the `component_total` evidence;
8. sends the known review question through the real local model;
9. verifies that Python rendered the exact grounded explanation;
10. verifies that the AI request did not change review state;
11. rejects an unconfirmed review decision;
12. saves a confirmed synthetic review and verifies the unresolved count changes from 6 to 5.

A successful run ends with:

```text
OFFLINE FULL STACK: PASS
External probes unavailable; MCP, web, SQLite, local AI and confirmed review all passed.
```

The test uses temporary SQLite state and synthetic data only.

## 4. Manual browser confirmation while still offline

After the automated offline test passes, keep external networking disabled and run:

```powershell
& $py scripts/run_web.py --model "qwen2.5:1.5b"
```

Open the private localhost session link. Do not share its token.

Create or reopen a synthetic review, select the `component_total` finding and ask:

> Why is this record flagged, and what should I verify?

The grounded explanation should state that `household_size` is recorded as 5 while the
validated component total is 4. Confirm that the interface remains usable while external
networking is disabled.

This manual step verifies browser rendering in the same offline state that the automated
gate checked.

## 5. Evidence to retain

Record:

- `requirements.lock.txt`;
- `docs/environment-lock.json`;
- the terminal output ending in `OFFLINE FULL STACK: PASS`;
- the measured local-model elapsed time;
- one screenshot of the browser result **without the private session token**.

Do not commit local databases, model weights, tokens, raw logs or real survey records.

## GitHub Actions boundary

No GitHub Actions workflow is required for this release-hardening stage. The maintainer's
reported Actions budget limitation remains independent of the local verification result.


## 6. Clean-install and packaging verification

With networking available, run:

```powershell
$py = ".\\.venv\\Scripts\\python.exe"
& $py scripts/check_clean_install.py
```

The script validates the committed lock hash and tested Python/platform metadata, creates
a fresh temporary virtual environment, installs the exact runtime snapshot, installs the
build backend required by `pyproject.toml`, installs FieldReady from the local checkout
without re-resolving runtime dependencies, runs `pip check`, executes the installed CLI
against the synthetic fixture and verifies bundled CSV/web assets.

It writes `runtime/clean-install-result.json`. A successful run ends with:

```text
CLEAN INSTALL + PACKAGING: PASS
```

The script reports the exact setuptools version resolved for the build. Because
`pyproject.toml` currently specifies `setuptools>=77`, that build-backend version is
evidence from the run rather than a pre-pinned supply-chain guarantee.

## 7. Broader local-model evaluation

Run:

```powershell
& $py scripts/evaluate_intent.py --model "qwen2.5:1.5b" --repeats 2
```

This executes 16 balanced synthetic cases twice (32 production-router evaluations) and writes `runtime/intent-eval.json`. The deterministic scope/routing layer must achieve 100% accuracy and recall for both scope classes. All in-scope cases must invoke the local model, all out-of-scope cases must be guarded without inference, and the advisory five-way review-focus classifier must achieve at least 75% accuracy. Model-only and end-to-end latency distributions are reported separately.


## Cross-platform lock hashing

The lock digest is defined over UTF-8 text with canonical LF line endings. Git may
materialise text as CRLF on Windows depending on checkout configuration, so raw-byte
hashing is not a valid cross-platform integrity check.

Both the lock writer and clean-install verifier now normalise CRLF/CR to LF before
calculating SHA-256. `.gitattributes` also requests LF for the lock and metadata files.
This changes neither the dependency pins nor the recorded digest; it makes verification
consistent across Windows and POSIX checkouts.
