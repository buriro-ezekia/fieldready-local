"""Compact M1 smoke check for versioned rules, review persistence and report export."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    from fieldready.reporting import export_review_package
    from fieldready.rule_engine import FIELD_RULESET, demo_bytes
    from fieldready.storage import Store

    try:
        with tempfile.TemporaryDirectory(prefix="fieldready-m1-") as folder:
            root = Path(folder)
            store = Store(root / "review.sqlite3")
            batch_id = store.register(demo_bytes(FIELD_RULESET), FIELD_RULESET)
            result = store.validate_batch(batch_id, "m1-smoke-validation")

            require(result["row_count"] == 14, "Unexpected M1 row count.")
            require(result["finding_count"] == 17, "Unexpected M1 finding count.")
            require(result["affected_rows"] == 13, "Unexpected M1 affected-row count.")
            require(
                result["severity_counts"] == {"critical": 3, "high": 9, "medium": 5},
                "Unexpected M1 severity counts.",
            )
            require(
                result["check_evaluations"] == {"evaluable": 80, "not_evaluable": 5},
                "Unexpected M1 rule-evaluation counts.",
            )

            first = store.list_findings(result["run_id"])["items"][0]
            store.decide(
                first["finding_id"], "confirmed", "M1 synthetic smoke review",
                first["revision"], "m1-smoke-review", confirmed=True,
            )
            require(store.summary(result["run_id"])["unresolved_findings"] == 16,
                    "Confirmed M1 review did not persist.")

            output = root / "review-package"
            exported = export_review_package(store, result["run_id"], output)
            require(exported["source_csv_included"] is False, "Export unexpectedly included source CSV.")

            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            require(manifest["finding_count"] == 17, "Manifest finding count is incorrect.")
            require(manifest["review_event_count"] == 1, "Manifest review-event count is incorrect.")
            for name, metadata in manifest["files"].items():
                digest = hashlib.sha256((output / name).read_bytes()).hexdigest()
                require(digest == metadata["sha256"], f"Manifest hash mismatch for {name}.")

            print(json.dumps({
                "ruleset": result["ruleset"],
                "rows": result["row_count"],
                "findings": result["finding_count"],
                "affected_rows": result["affected_rows"],
                "severity_counts": result["severity_counts"],
                "check_evaluations": result["check_evaluations"],
                "unresolved_after_one_confirmation": 16,
                "export_files": exported["files"],
                "source_csv_included": exported["source_csv_included"],
            }, indent=2))
        print("M1 VERSIONED RULES + REPORT: PASS")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print("M1 CHECK: FAIL — " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
