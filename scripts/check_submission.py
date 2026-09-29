"""Audit the repository for hackathon-submission hygiene and unresolved confirmations."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "requirements.lock.txt",
    "docs/demo-script.md",
    "docs/devpost-submission.md",
    "docs/submission-assets.md",
    "docs/submission-requirements-map.md",
    "docs/youtube-upload.md",
    "docs/m1-verification.md",
    "docs/rulesets.md",
)

BLOCKED_PREFIXES = (
    "runtime/",
    "outputs/",
    "local/",
    ".fieldready-local/",
)

BLOCKED_SUFFIXES = (
    ".sqlite",
    ".sqlite3",
    ".db",
    ".log",
    ".gguf",
    ".safetensors",
    ".ckpt",
)

PLACEHOLDER_MARKERS = (
    "REQUIRES_CONFIRMATION_VIDEO_URL",
    "REQUIRES_CONFIRMATION_MINI_CHALLENGE",
    "REQUIRES_CONFIRMATION_PRE_EXISTING_WORK",
)

TOKEN_PATTERNS = (
    ("browser session token", re.compile(r"#token=[A-Za-z0-9_-]{32,128}")),
    ("bearer credential", re.compile(r"Bearer\s+[A-Za-z0-9_-]{32,128}")),
)

WINDOWS_USER_PATH = re.compile(r"[A-Za-z]:\\Users\\[^\\\r\n]+\\")


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or "git command failed")
    return completed.stdout


def tracked_files() -> list[str]:
    output = run_git("ls-files", "-z")
    return [item for item in output.split("\0") if item]


def current_branch() -> str:
    return run_git("branch", "--show-current").strip()


def scan_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hygiene-only",
        action="store_true",
        help="Ignore human confirmation placeholders but still enforce repository safety.",
    )
    args = parser.parse_args()

    blockers: list[str] = []
    warnings: list[str] = []

    try:
        tracked = tracked_files()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("SUBMISSION AUDIT: FAIL — cannot inspect Git tracking: " + str(exc), file=sys.stderr)
        return 2

    tracked_set = set(tracked)

    try:
        branch = current_branch()
        if not args.hygiene_only and branch != "main":
            blockers.append(
                "Final submission audit must run from main; current branch is "
                + (branch or "(detached HEAD)") + "."
            )
        elif args.hygiene_only and branch != "main":
            warnings.append(
                "Development branch in use: " + (branch or "(detached HEAD)")
                + ". Final audit will require main after the verified branch is merged."
            )
    except RuntimeError as exc:
        blockers.append("Could not determine current Git branch: " + str(exc))

    for required in REQUIRED_FILES:
        if required not in tracked_set or not (ROOT / required).is_file():
            blockers.append("Missing required tracked file: " + required)

    licence = ROOT / "LICENSE"
    if licence.is_file():
        text = licence.read_text(encoding="utf-8", errors="replace")
        if "Apache License" not in text or "Version 2.0" not in text:
            blockers.append("LICENSE does not appear to contain Apache License 2.0 text.")

    for name in tracked:
        normal = name.replace("\\", "/")
        lower = normal.lower()
        if lower in {".env", ".env.local", ".env.production"}:
            blockers.append("Tracked environment file: " + name)
        if any(lower.startswith(prefix) for prefix in BLOCKED_PREFIXES):
            blockers.append("Tracked runtime/output artefact: " + name)
        if any(lower.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
            blockers.append("Tracked database/log/model artefact: " + name)

        text = scan_text(ROOT / name)
        if text is None:
            continue

        for label, pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                blockers.append(f"Possible tracked {label}: {name}")

        if WINDOWS_USER_PATH.search(text):
            blockers.append("Personal-looking Windows user path in tracked text: " + name)

    submission_path = ROOT / "docs" / "devpost-submission.md"
    if submission_path.is_file():
        submission = submission_path.read_text(encoding="utf-8")
        unresolved = [marker for marker in PLACEHOLDER_MARKERS if marker in submission]
        if unresolved:
            if args.hygiene_only:
                warnings.append(
                    "Human confirmations remain unresolved: " + ", ".join(unresolved)
                )
            else:
                blockers.append(
                    "Human confirmations remain unresolved: " + ", ".join(unresolved)
                )

        if "https://github.com/buriro-ezekia/fieldready-local" not in submission:
            blockers.append("Devpost package is missing the public repository URL.")
        if "Alexa+" not in submission or "MCP" not in submission:
            blockers.append("Devpost package is missing the Alexa+/MCP track description.")

        open_source_requirements = {
            "Open Source mini challenge selection": "## Mini challenge\n\n**Open Source.**",
            "Open Source contribution URL": "https://github.com/buriro-ezekia/fieldready-local/pull/5",
            "Open Source project repository URL": "https://github.com/buriro-ezekia/fieldready-local",
            "Open Source GitHub username": "**GitHub username:** `buriro-ezekia`",
            "Open Source contribution description": "### Open Source contribution description",
            "AWS Builder opt-out": "### AWS Builder Mini Challenge\n\n**No.**",
        }
        for label, required_text in open_source_requirements.items():
            if required_text not in submission:
                blockers.append("Devpost package is missing: " + label + ".")

        if "FieldReady Local was created during the hackathon submission window." not in submission:
            blockers.append("Devpost package is missing the confirmed pre-existing-work disclosure.")

    try:
        status = run_git("status", "--porcelain")
        if status.strip():
            warnings.append("Working tree is not clean; review local changes before final submission.")
    except RuntimeError as exc:
        warnings.append("Could not inspect working-tree cleanliness: " + str(exc))

    print("SUBMISSION AUDIT")
    print("================")
    print("Tracked files:", len(tracked))
    print("Submission branch:",
          "PASS (main)" if "branch" in locals() and branch == "main" else
          ("IGNORED (hygiene-only)" if args.hygiene_only else "BLOCKED"))
    print("Required files:", "PASS" if not any("Missing required" in b for b in blockers) else "FAIL")
    print("Sensitive/runtime artefacts:",
          "PASS" if not any("artefact" in b or "environment file" in b for b in blockers) else "FAIL")
    print("Credential/path scan:",
          "PASS" if not any("credential" in b or "session token" in b or "Windows user path" in b
                            for b in blockers) else "FAIL")
    devpost_blocked = any(
        blocker.startswith("Devpost package") or "confirmations remain" in blocker
        for blocker in blockers
    )
    print("Devpost confirmations:",
          "IGNORED (hygiene-only)" if args.hygiene_only else
          ("PASS" if not devpost_blocked else "BLOCKED"))

    if warnings:
        print("\nWARNINGS")
        for warning in warnings:
            print("-", warning)

    if blockers:
        print("\nBLOCKERS")
        for blocker in blockers:
            print("-", blocker)
        print("\nSUBMISSION AUDIT: BLOCKED")
        return 2

    print("\nSUBMISSION AUDIT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
