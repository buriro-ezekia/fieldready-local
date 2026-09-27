"""Real web HTTP -> MCP -> SQLite check. Does NOT launch a browser or run a model."""
import argparse
import asyncio
import http.client
import importlib.util
import json
import secrets
import socket
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def request(port, token, path, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=40)
    try:
        connection.request("GET" if body is None else "POST", path,
                           body=json.dumps(body) if body is not None else None,
                           headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


@contextmanager
def web_server(db, gateway, token):
    import uvicorn
    from fieldready.web_app import WebApp

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(WebApp(db, gateway, token, port),
        host="127.0.0.1", port=port, access_log=False, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Web server did not become ready.")
            time.sleep(0.05)
        yield port
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if thread.is_alive():
            raise RuntimeError("Web server failed to shut down cleanly.")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    missing = [m for m in ("mcp", "httpx2", "uvicorn") if importlib.util.find_spec(m) is None]
    if missing:
        print("WEB/MCP CHECK: NOT RUN — missing " + ", ".join(missing), file=sys.stderr)
        return 2
    from check_mcp import serve
    from fieldready.mcp_client import MCPGateway

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    with tempfile.TemporaryDirectory(prefix="fieldready-web-") as folder:
        db = Path(folder) / "test.sqlite3"
        mcp_token, web_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with serve(db, mcp_token) as url:
            mcp_port = int(url.split(":")[2].split("/")[0])
            gateway = MCPGateway(mcp_port, mcp_token)
            health = asyncio.run(gateway.ping())
            require(health["protocol"] >= "2025-11-25", "MCP health probe negotiated an old protocol.")
            require(set(health["tools"]) == {"validate_batch", "list_findings", "get_review_summary"},
                    "MCP health probe found an unexpected tool surface.")
            print("MCP health probe:", health["protocol"], ", ".join(health["tools"]))
            with web_server(db, gateway, web_token) as port:
                require(request(port, "wrong", "/api/info")[0] == 401, "Missing authentication was accepted.")
                status, initial = request(port, web_token, "/api/demo", {"request_id": "web-demo"})
                require(status == 200 and initial["finding_count"] == 6, "Web/MCP validation failed.")
                run = initial["run_id"]
                status, data = request(port, web_token, "/api/run", {"run_id": run})
                require(status == 200 and len(data["page"]["items"]) == 6, "Web findings failed.")
                first = data["page"]["items"][0]
                decision = {"finding_id": first["finding_id"], "status": "confirmed", "reason": "Synthetic web test",
                            "expected_revision": 0, "request_id": "web-review", "confirmed": False}
                require(request(port, web_token, "/api/decision", decision)[0] == 400, "Unconfirmed write accepted.")
                decision["confirmed"] = True
                require(request(port, web_token, "/api/decision", decision)[0] == 200, "Confirmed write failed.")
                require(request(port, web_token, "/api/decision", decision)[0] == 200, "Idempotent replay failed.")
        with serve(db, mcp_token) as url:
            mcp_port = int(url.split(":")[2].split("/")[0])
            with web_server(db, MCPGateway(mcp_port, mcp_token), web_token) as port:
                status, data = request(port, web_token, "/api/run", {"run_id": run})
                summary = data["summary"]
                require(status == 200 and summary["unresolved_findings"] == 5, "Review did not survive restart.")
                require(summary["review_counts"]["confirmed"] == 1, "Review was duplicated.")
                print(json.dumps(summary, indent=2))
    print("WEB HTTP -> MCP -> SQLITE + RESTART: PASS (browser rendering and local inference NOT tested)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
