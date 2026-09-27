"""Verify FieldReady installs and runs from a fresh temporary virtual environment.

This gate may use package indexes to populate the clean environment. It does not test
offline runtime; scripts/check_offline.py covers that separately.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock.txt"
META = ROOT / "docs" / "environment-lock.json"


def run(python: Path, *args: str, timeout: int = 300) -> str:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [str(python), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode:
        detail = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
        raise RuntimeError(detail or f"Command failed: {' '.join(args)}")
    return completed.stdout


def executable(env_dir: Path) -> Path:
    return env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def verify_lock() -> dict:
    if not LOCK.is_file() or not META.is_file():
        raise RuntimeError("Committed lock files are missing.")
    metadata = json.loads(META.read_text(encoding="utf-8"))
    digest = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    if digest != metadata.get("lock_sha256"):
        raise RuntimeError("requirements.lock.txt does not match docs/environment-lock.json.")
    if platform.python_version() != metadata.get("python_version"):
        raise RuntimeError(
            f"Use the tested Python {metadata.get('python_version')}; current is {platform.python_version()}."
        )
    if platform.system() != "Windows" or not str(metadata.get("platform", "")).startswith("Windows"):
        raise RuntimeError("The committed dependency snapshot is Windows-specific.")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="Keep the clean environment under runtime/clean-install-env for inspection.")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "runtime" / "clean-install-result.json")
    args = parser.parse_args()

    try:
        metadata = verify_lock()
        if args.keep:
            env_dir = ROOT / "runtime" / "clean-install-env"
            if env_dir.exists():
                shutil.rmtree(env_dir)
            env_dir.parent.mkdir(parents=True, exist_ok=True)
            cleanup = None
        else:
            cleanup = tempfile.TemporaryDirectory(prefix="fieldready-clean-")
            env_dir = Path(cleanup.name) / "venv"

        try:
            subprocess.run([sys.executable, "-m", "venv", str(env_dir)],
                           cwd=ROOT, check=True, timeout=120)
            py = executable(env_dir)
            if not py.is_file():
                raise RuntimeError("Fresh virtual environment did not create a Python executable.")

            # Install the exact runtime snapshot first.
            run(py, "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                "-r", str(LOCK), timeout=600)

            # Build backend is a packaging dependency, not part of the runtime snapshot.
            run(py, "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                "setuptools>=77", timeout=300)
            setuptools_version = run(
                py, "-c", "import importlib.metadata as m; print(m.version('setuptools'))"
            ).strip()

            # Install FieldReady from this checkout without re-resolving runtime dependencies.
            run(py, "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                "--no-build-isolation", "--no-deps", ".", timeout=300)
            run(py, "-m", "pip", "check")

            with tempfile.TemporaryDirectory(prefix="fieldready-clean-db-") as folder:
                db = Path(folder) / "clean.sqlite3"
                output = run(py, "-m", "fieldready.cli", "--db", str(db), "demo")
                result = json.loads(output)
                if result.get("row_count") != 8 or result.get("finding_count") != 6:
                    raise RuntimeError("Installed CLI returned unexpected synthetic validation counts.")

                # Prove package data/assets are present in the installed wheel/package.
                probe = (
                    "from importlib.resources import files;"
                    "p=files('fieldready');"
                    "assert p.joinpath('data/survey.csv').is_file();"
                    "assert p.joinpath('web_assets/index.html').is_file();"
                    "print('PACKAGE DATA: PASS')"
                )
                package_probe = run(py, "-c", probe).strip()

            report = {
                "python_version": metadata["python_version"],
                "runtime_lock_sha256": metadata["lock_sha256"],
                "runtime_package_count": metadata["package_count"],
                "setuptools_version_resolved_for_build": setuptools_version,
                "installed_demo_row_count": result["row_count"],
                "installed_demo_finding_count": result["finding_count"],
                "package_data": package_probe,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, indent=2))
            print("WROTE:", args.output)
            print("CLEAN INSTALL + PACKAGING: PASS")
            print("Note: setuptools is currently range-constrained by pyproject.toml; its resolved version is reported above.")
            return 0
        finally:
            if cleanup is not None:
                cleanup.cleanup()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print("CLEAN INSTALL CHECK: FAIL — " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
