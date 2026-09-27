"""Verify one real local Ollama explanation; never download or use cloud inference."""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@contextmanager
def ollama_service(executable: str, port: int):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    env["OLLAMA_NO_CLOUD"] = "1"
    with tempfile.TemporaryFile(mode="w+b") as log:
        child = subprocess.Popen([executable, "serve"], env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 30
            while True:
                if child.poll() is not None:
                    log.seek(0)
                    raise RuntimeError("Local Ollama exited: " + log.read(8000).decode(errors="replace"))
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Local Ollama did not start within 30 seconds.")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:1.5b",
                        help="Exact model already installed in Ollama; nothing is downloaded.")
    parser.add_argument("--port", type=int, default=11435)
    args = parser.parse_args()

    ollama = shutil.which("ollama")
    if not ollama:
        print("LOCAL MODEL CHECK: NOT RUN — Ollama is not installed or not on PATH.", file=sys.stderr)
        return 2

    from fieldready.local_model import LocalExplainer

    summary = {
        "row_count": 8,
        "finding_count": 6,
        "affected_rows": 6,
        "unresolved_findings": 6,
    }
    finding = {
        "finding_id": "0" * 32 + ":1",
        "row_number": 2,
        "rule_id": "component_total",
        "field": "household_size",
        "severity": "high",
        "observed": "5",
        "expected": "4",
        "status": "open",
    }
    question = "Why was this finding raised, and what should the supervisor verify?"

    try:
        with ollama_service(ollama, args.port):
            explainer = LocalExplainer(args.model, args.port)
            result = explainer.explain(summary, finding, question)
    except (OSError, RuntimeError, ValueError) as exc:
        print("LOCAL MODEL CHECK: FAIL — " + str(exc), file=sys.stderr)
        print("No model was downloaded and no cloud fallback was used.", file=sys.stderr)
        return 2

    expected = {
        "rule_id": "component_total",
        "record_ordinal": 2,
        "observed": "5",
        "expected": "4",
        "finding_id": finding["finding_id"],
        "intent": "in_scope",
    }
    changed = {key: (expected[key], result.get(key)) for key in expected if result.get(key) != expected[key]}
    if changed:
        print("LOCAL MODEL CHECK: FAIL — returned evidence reference changed unexpectedly.", file=sys.stderr)
        print("MISMATCH:", changed, file=sys.stderr)
        return 2

    print("LOCAL MODEL:", result["model"])
    print("MODEL DIGEST:", result.get("digest"))
    print("ELAPSED SECONDS:", result["elapsed_seconds"])
    print("LOCAL MODEL INTENT:", result["intent"])
    print("GROUNDED OUTPUT:")
    print(result["text"])
    print("LOCAL MODEL + GROUNDED EXPLANATION: PASS (broader intent quality is not yet evaluated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
