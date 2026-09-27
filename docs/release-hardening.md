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
