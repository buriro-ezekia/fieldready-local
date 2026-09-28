"""Opt-in real HTTP check. A missing SDK is NOT a successful integration test."""
import asyncio
import importlib.util
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


@contextmanager
def serve(db: Path, token: str):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env["FIELDREADY_MCP_TOKEN"] = token
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    # An ephemeral-port race is possible: a startup failure is reported, never hidden.
    with tempfile.TemporaryFile(mode="w+b") as logs:
        process = subprocess.Popen([sys.executable, "-m", "fieldready.mcp_server", "--db", str(db),
                                    "--port", str(port)], env=env, stdout=logs, stderr=logs)
        try:
            deadline = time.monotonic() + 20
            while True:
                if process.poll() is not None:
                    logs.seek(0)
                    raise RuntimeError("MCP server exited: " + logs.read().decode(errors="replace"))
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("MCP server did not become ready.")
                    time.sleep(0.1)
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


async def verify(url: str, token: str, batch_id: str, previous_run: str | None = None):
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    async with httpx2.AsyncClient(headers={"Authorization": "Bearer " + token},
                                  timeout=15, trust_env=False) as http:
        async with Client(streamable_http_client(url, http_client=http)) as client:
            require(client.protocol_version >= "2025-11-25", "Negotiated MCP version is too old.")
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            require(names == {"validate_batch", "list_findings", "get_review_summary"},
                    "Unexpected tool exposure.")
            if previous_run:
                result = await client.call_tool("get_review_summary", {"run_id": previous_run})
                require(not result.is_error, "Summary failed after restart.")
                require(result.structured_content["unresolved_findings"] == 5,
                        "The confirmed review did not persist.")
                return result.structured_content
            result = await client.call_tool("validate_batch", {"batch_id": batch_id, "request_id": "http-demo"})
            require(not result.is_error, "MCP validation returned a tool error.")
            summary = result.structured_content
            require(summary["finding_count"] == 6 and summary["row_count"] == 8, "Incorrect MCP counts.")
            page = await client.call_tool("list_findings", {"run_id": summary["run_id"]})
            require(not page.is_error and len(page.structured_content["items"]) == 6, "Findings were not returned.")
            denied = await client.call_tool("apply_decision", {})
            require(denied.is_error, "A forbidden review-write tool was accepted.")
            print("Negotiated MCP protocol:", client.protocol_version)
            return {**summary, "finding_id": page.structured_content["items"][0]["finding_id"]}


def main() -> int:
    missing = [name for name in ("mcp", "uvicorn", "httpx2") if importlib.util.find_spec(name) is None]
    if missing:
        print("MCP INTEGRATION: NOT RUN — missing dependencies: " + ", ".join(missing), file=sys.stderr)
        print('Install the project extra in a virtual environment: python -m pip install -e ".[mcp]"', file=sys.stderr)
        return 2
    from fieldready.storage import Store
    with tempfile.TemporaryDirectory(prefix="fieldready-mcp-") as folder:
        db = Path(folder) / "test.sqlite3"
        store = Store(db)
        batch_id = store.register(files("fieldready").joinpath("data/survey.csv").read_bytes())
        token = secrets.token_urlsafe(32)
        with serve(db, token) as url:
            initial = asyncio.run(asyncio.wait_for(verify(url, token, batch_id), timeout=45))
        subprocess.run([sys.executable, str(ROOT / "scripts/fieldready.py"), "--db", str(db),
                        "review", initial["finding_id"], "--status", "confirmed", "--reason",
                        "Synthetic MCP integration review", "--revision", "0", "--request-id",
                        "http-review", "--confirm"], check=True, capture_output=True, timeout=10)
        with serve(db, token) as url:
            persisted = asyncio.run(asyncio.wait_for(verify(url, token, batch_id, initial["run_id"]), timeout=45))
        print(json.dumps(persisted, indent=2))
    print("MCP HTTP + RESTART PERSISTENCE: PASS (does not test browser or model inference)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
