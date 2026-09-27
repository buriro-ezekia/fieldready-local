# Local setup

## Core development

The core requires Python 3.11+ and no external packages. Tested here with Python 3.13.5
on Linux; Windows execution remains to be verified. From the repository root:

```powershell
python scripts/check_local.py
python scripts/fieldready.py demo
```

All tests use temporary directories; the demo stores its database under your user home.
To place demo data elsewhere, use `python scripts/fieldready.py --db PATH demo`.
Do not point this at a production database. The schema is v1 with no migration framework
yet; an unknown version is rejected rather than overwritten.

The CLI prints errors on stderr and returns non-zero for invalid input. Review changes
require all of: a finding ID, permitted status, reason, current revision, unique request
ID and `--confirm`. Repeating an identical request ID/payload returns the original event;
reusing it for another change is rejected. Reload after a stale-revision error.

## Install and verify the optional MCP adapter

Windows PowerShell, without changing the global Python installation:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
.\.venv\Scripts\python.exe scripts/check_local.py --integration
```

Linux/macOS: replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.
Package downloads require internet access. These commands were not successfully
executed in the initial sandbox: name resolution for package-download hosts failed.
The optional dependency ranges target current SDK v2 documentation, not a tested lock.
Once installation and HTTP checks pass, resolve and commit `uv.lock`; do not invent it.

## Start the server manually after the integration check passes

In PowerShell, with the MCP extra installed:

```powershell
$env:FIELDREADY_MCP_TOKEN = (.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))")
.\.venv\Scripts\python.exe -m fieldready.mcp_server
```

This listens at `http://127.0.0.1:8000/mcp`. Import a synthetic CSV using the trusted
CLI and give the client its returned batch ID. The client must send
`Authorization: Bearer <locally generated token>`. Do not paste the token into a
prompt, commit, screenshot or public issue. No automatic `.env` loading is implemented.

`check_mcp.py` handles its own temporary database, random token, ports and server
shutdown. It neither installs packages nor requests a GitHub runner.

## Failure classification

| Observation | Interpretation |
| --- | --- |
| A test prints a failing assertion | Investigate the code, test or assumptions. |
| MCP check says dependencies are missing | Integration did not run; install and retry locally. |
| GitHub says a job could not start due to budget | Infrastructure constraint; no code result was produced. |
| CLI works but browser/model has not run | Core demonstration only, not complete M0. |

Do not raise a GitHub budget or register a public self-hosted runner to bypass this
constraint. No automated Actions workflow is included in this contribution.
