"""Run all core tests; optionally require, rather than silently skip, MCP tests."""
import argparse
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    print("CORE CHECKS: PASS (not evidence of MCP, browser or local-model execution)", flush=True)
    if args.integration:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.call([sys.executable, str(ROOT / "scripts/check_mcp.py")], env=env)
    print("MCP / browser / model / Windows execution: not checked by this command.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
