"""Launch the local browser and owned MCP/Ollama services; never use hosted services."""
import argparse
import asyncio
import importlib.util
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@contextmanager
def service(command, port, env):
    # Do not reuse or terminate a service that somebody else started on this port.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    with tempfile.TemporaryFile(mode="w+b") as log:
        child = subprocess.Popen(command, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 30
            while True:
                if child.poll() is not None:
                    log.seek(0)
                    raise RuntimeError("Local service exited: " + log.read(8000).decode(errors="replace"))
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Local service did not start within the readiness limit.")
                    time.sleep(0.1)
            yield
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)


def wait_for_mcp(gateway, timeout=10):
    """Wait for an MCP handshake and exact tool discovery; do not call a fake tool request."""
    deadline = time.monotonic() + timeout
    last_error = None
    while True:
        try:
            return asyncio.run(gateway.ping())
        except RuntimeError as exc:
            last_error = exc
            if time.monotonic() >= deadline:
                raise RuntimeError("MCP server opened its port but did not become protocol-ready.") from last_error
            time.sleep(0.2)


def main() -> int:
    from fieldready.mcp_client import MCPGateway
    from fieldready.local_model import LocalAIServiceExplainer, LocalExplainer
    from fieldready.web_app import WebApp

    parser = argparse.ArgumentParser(description="FieldReady Local browser prototype")
    home = Path(os.environ.get("FIELDREADY_HOME", str(Path.home() / ".fieldready-local")))
    parser.add_argument("--db", type=Path, default=home / "fieldready.sqlite3")
    parser.add_argument("--web-port", type=int, default=8501)
    parser.add_argument("--mcp-port", type=int, default=8000)
    parser.add_argument("--ollama-port", type=int, default=11435)
    parser.add_argument("--ai-service-port", type=int,
                        help="Existing reusable local AI service port; uses it instead of starting Ollama")
    parser.add_argument("--model",
                        help="Exact installed local model; optional in AI-service mode, otherwise enables direct Ollama")
    args = parser.parse_args()
    missing = [m for m in ("mcp", "httpx2", "uvicorn") if importlib.util.find_spec(m) is None]
    if missing:
        print('Missing dependencies: ' + ', '.join(missing) + '. Run: python -m pip install -e ".[mcp]"', file=sys.stderr)
        return 2
    import uvicorn

    ports = [args.web_port, args.mcp_port]
    if args.ai_service_port:
        ports.append(args.ai_service_port)
    elif args.model:
        ports.append(args.ollama_port)
    if len(ports) != len(set(ports)) or any(not 1 <= p <= 65535 for p in ports):
        parser.error("Use distinct local ports between 1 and 65535.")
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.web_port))
        token, mcp_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        gateway = MCPGateway(args.mcp_port, mcp_token)
        if args.ai_service_port:
            explainer = LocalAIServiceExplainer(args.ai_service_port, args.model)
            explainer.probe()
        elif args.model:
            explainer = LocalExplainer(args.model, args.ollama_port)
        else:
            explainer = None
        app = WebApp(args.db, gateway, token, args.web_port, explainer)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        env["FIELDREADY_MCP_TOKEN"] = mcp_token
        with ExitStack() as stack:
            stack.enter_context(service([sys.executable, "-m", "fieldready.mcp_server",
                                         "--db", str(args.db), "--port", str(args.mcp_port)], args.mcp_port, env))
            health = wait_for_mcp(gateway)
            if args.model and not args.ai_service_port:
                ollama = shutil.which("ollama")
                if not ollama:
                    raise ValueError("Ollama is not installed or not on PATH. Omit --model to use the review UI.")
                model_env = env | {"OLLAMA_HOST": f"127.0.0.1:{args.ollama_port}", "OLLAMA_NO_CLOUD": "1"}
                stack.enter_context(service([ollama, "serve"], args.ollama_port, model_env))
            print(f"MCP ready: protocol {health['protocol']}; tools: {', '.join(health['tools'])}", flush=True)
            print("Open this LOCAL SESSION LINK in your browser; keep the full link private:", flush=True)
            print(f"http://127.0.0.1:{args.web_port}/#token={token}", flush=True)
            if args.ai_service_port:
                ai_status = f"{explainer.model} via reusable service 127.0.0.1:{args.ai_service_port}"
            else:
                ai_status = args.model or "disabled (review workflow remains available)"
            print("AI: " + ai_status, flush=True)
            print("Press Ctrl+C here to stop the browser server and its owned services.", flush=True)
            uvicorn.run(app, host="127.0.0.1", port=args.web_port, access_log=False, log_level="warning")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
