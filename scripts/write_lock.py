"""Capture exact installed package versions from the tested virtual environment.

This creates requirements.lock.txt plus docs/environment-lock.json. It never resolves
or downloads packages; it only records the environment that is already installed.
"""
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock.txt"
META = ROOT / "docs" / "environment-lock.json"
REQUIRED = {"mcp", "uvicorn", "httpx2"}


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def run(*args: str) -> str:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"Command failed: {' '.join(args)}")
    return completed.stdout


def main() -> int:
    if sys.prefix == sys.base_prefix:
        print("LOCK SNAPSHOT: FAIL — run with the project's virtual-environment Python.", file=sys.stderr)
        return 2

    try:
        run("-m", "pip", "check")
        try:
            frozen = run("-m", "pip", "freeze", "--all", "--exclude-editable")
        except RuntimeError:
            frozen = run("-m", "pip", "freeze", "--all")
    except RuntimeError as exc:
        print("LOCK SNAPSHOT: FAIL — " + str(exc), file=sys.stderr)
        return 2

    pins = []
    for raw in frozen.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-e "):
            continue
        # Never lock the current project itself, whether editable, direct-url or installed.
        candidate_name = line.split(" @ ", 1)[0].split("==", 1)[0].strip()
        if canonical(candidate_name) == "fieldready-local":
            continue
        if "==" not in line:
            print("LOCK SNAPSHOT: FAIL — non-version-pinned dependency encountered: " + line,
                  file=sys.stderr)
            return 2
        name, version = line.split("==", 1)
        if not name.strip() or not version.strip():
            print("LOCK SNAPSHOT: FAIL — invalid freeze entry: " + line, file=sys.stderr)
            return 2
        pins.append((canonical(name), f"{name}=={version}"))

    by_name = {name: line for name, line in pins}
    missing = sorted(REQUIRED - set(by_name))
    if missing:
        print("LOCK SNAPSHOT: FAIL — tested MCP environment is missing: " + ", ".join(missing),
              file=sys.stderr)
        return 2

    body_lines = [
        "# FieldReady Local exact-version environment snapshot",
        "# Generated from the maintainer-tested virtual environment; no packages were resolved here.",
        f"# Python {platform.python_version()} ({platform.python_implementation()})",
        "",
        *[line for _, line in sorted(pins)],
        "",
    ]
    body = "\n".join(body_lines)
    LOCK.write_text(body, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    metadata = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "package_count": len(pins),
        "required_roots_present": sorted(REQUIRED),
        "pip_check": "pass",
        "lock_file": LOCK.name,
        "lock_sha256": digest,
        "note": (
            "Exact-version environment snapshot from the tested virtual environment. "
            "It is not a hash-locked wheel supply-chain manifest."
        ),
    }
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"LOCK SNAPSHOT: PASS — {len(pins)} packages")
    print("WROTE:", LOCK.relative_to(ROOT))
    print("WROTE:", META.relative_to(ROOT))
    print("SHA256:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
