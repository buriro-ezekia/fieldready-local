"""Prove the core FieldReady stack works while external connectivity is unavailable.

Disconnect external networking first. This script deliberately refuses to count an
online run as offline evidence. It uses only synthetic data and temporary SQLite state.
"""
import argparse
import asyncio
import json
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

EXTERNAL_PROBES = (
    ("1.1.1.1", 443, "Cloudflare public endpoint"),
    ("8.8.8.8", 53, "Google public DNS endpoint"),
    ("github.com", 443, "GitHub HTTPS endpoint"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def prove_external_network_unavailable() -> list[dict]:
    results = []
    for host, port, label in EXTERNAL_PROBES:
        try:
            with socket.create_connection((host, port), timeout=1.5):
                raise RuntimeError(
                    f"OFFLINE GATE: FAIL — external connection succeeded: {label} ({host}:{port}). "
                    "Disconnect Wi-Fi/Ethernet or otherwise disable external networking, then rerun."
                )
        except RuntimeError:
            raise
        except OSError as exc:
            results.append({
                "target": f"{host}:{port}",
                "label": label,
                "result": "unreachable",
                "error_type": type(exc).__name__,
            })
    return results


def run_local_check(*args: str) -> None:
    completed = subprocess.run([sys.executable, *args], cwd=ROOT, timeout=180)
    if completed.returncode:
        raise RuntimeError("Local verification command failed: " + " ".join(args))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:1.5b",
                        help="Exact Ollama model already installed locally; nothing is downloaded.")
    args = parser.parse_args()

    if sys.prefix == sys.base_prefix:
        print("OFFLINE CHECK: FAIL — use the project's virtual-environment Python.", file=sys.stderr)
        return 2
    if not shutil.which("ollama"):
        print("OFFLINE CHECK: FAIL — Ollama is not installed or not on PATH.", file=sys.stderr)
        return 2

    try:
        probes = prove_external_network_unavailable()
        print("OFFLINE GATE: PASS — external probes were unreachable")
        print(json.dumps(probes, indent=2))

        run_local_check("-m", "pip", "check")
        run_local_check("scripts/check_local.py", "--integration")
        run_local_check("scripts/check_web.py")

        from check_mcp import serve
        from check_model import ollama_service
        from check_web import request, web_server
        from fieldready.local_model import LocalExplainer, grounded_text
        from fieldready.mcp_client import MCPGateway

        with tempfile.TemporaryDirectory(prefix="fieldready-offline-") as folder:
            db = Path(folder) / "offline.sqlite3"
            mcp_token = secrets.token_urlsafe(32)
            web_token = secrets.token_urlsafe(32)
            ollama_port = free_port()

            with serve(db, mcp_token) as url:
                mcp_port = int(url.split(":")[2].split("/")[0])
                gateway = MCPGateway(mcp_port, mcp_token)
                health = asyncio.run(gateway.ping())
                require(health["protocol"] >= "2025-11-25", "Offline MCP protocol is too old.")

                with ollama_service(shutil.which("ollama"), ollama_port):
                    explainer = LocalExplainer(args.model, ollama_port)
                    with web_server(db, gateway, web_token, explainer) as web_port:
                        status, info = request(web_port, web_token, "/api/info")
                        require(status == 200 and info["model"] == args.model,
                                "Offline web app did not expose the configured local model.")

                        status, initial = request(
                            web_port, web_token, "/api/demo", {"request_id": "offline-demo"}
                        )
                        require(status == 200 and initial["finding_count"] == 6,
                                "Offline demo validation failed.")
                        run_id = initial["run_id"]

                        status, data = request(web_port, web_token, "/api/run", {"run_id": run_id})
                        require(status == 200, "Offline evidence retrieval failed.")
                        items = data["page"]["items"]
                        finding = next((item for item in items if item["rule_id"] == "component_total"), None)
                        require(finding is not None, "Offline component_total finding was not returned.")
                        require(data["summary"]["unresolved_findings"] == 6,
                                "Unexpected review state before local AI request.")

                        question = "Why is this record flagged, and what should I verify?"
                        status, explanation = request(web_port, web_token, "/api/explain", {
                            "run_id": run_id,
                            "finding_id": finding["finding_id"],
                            "question": question,
                        })
                        require(status == 200, "Offline local-AI explanation failed.")
                        require(explanation["model"] == args.model, "Unexpected offline model identity.")
                        require(explanation["intent"] == "in_scope", "Deterministic scope guard rejected a known review question.")
                        require(explanation["routing_source"] == "local_model_focus"
                                and explanation["model_invoked"] is True,
                                "Offline local AI focus classification did not run.")
                        require(explanation["focus"] in {"reason", "verification", "evidence", "review_guidance", "combined"},
                                "Offline local AI returned an unsupported focus.")
                        require(explanation["text"] == grounded_text(finding),
                                "Offline explanation was not deterministic evidence rendering.")

                        status, unchanged = request(web_port, web_token, "/api/run", {"run_id": run_id})
                        require(status == 200 and unchanged["summary"]["unresolved_findings"] == 6,
                                "AI explanation changed review state.")

                        decision = {
                            "finding_id": finding["finding_id"],
                            "status": "confirmed",
                            "reason": "Offline synthetic verification",
                            "expected_revision": finding["revision"],
                            "request_id": "offline-review",
                            "confirmed": False,
                        }
                        require(request(web_port, web_token, "/api/decision", decision)[0] == 400,
                                "Offline control surface accepted an unconfirmed decision.")
                        decision["confirmed"] = True
                        require(request(web_port, web_token, "/api/decision", decision)[0] == 200,
                                "Offline confirmed decision failed.")

                        status, final = request(web_port, web_token, "/api/run", {"run_id": run_id})
                        require(status == 200 and final["summary"]["unresolved_findings"] == 5,
                                "Offline confirmed review was not persisted.")

                        print("OFFLINE MODEL:", explanation["model"])
                        print("OFFLINE MODEL FOCUS:", explanation["focus"])
                        print("OFFLINE MODEL ELAPSED SECONDS:", explanation["elapsed_seconds"])
                        print("OFFLINE GROUNDED OUTPUT:")
                        print(explanation["text"])

        print("OFFLINE FULL STACK: PASS")
        print("External probes unavailable; MCP, web, SQLite, local AI and confirmed review all passed.")
        return 0

    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print("OFFLINE CHECK: FAIL — " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
