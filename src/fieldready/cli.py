"""Trusted local control surface; model-facing MCP remains read-only."""

import argparse
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path

from fieldready.rule_engine import FIELD_RULESET, LEGACY_RULESET, demo_bytes, list_rulesets
from fieldready.rules import MAX_BYTES
from fieldready.storage import STATUSES, Store


def default_db() -> Path:
    home = Path(os.environ.get("FIELDREADY_HOME", str(Path.home() / ".fieldready-local")))
    return home / "fieldready.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description="FieldReady Local — local survey-review assistant")
    parser.add_argument("--db", type=Path, default=default_db())
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("rulesets", help="List packaged versioned rulesets")
    sub.add_parser("demo", help="Import and validate the original four-column synthetic batch")
    sub.add_parser("demo-field", help="Import and validate the richer field-survey demonstration")

    ingest = sub.add_parser("import-csv", help="Import a local CSV against an explicit packaged ruleset")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--ruleset", default=LEGACY_RULESET,
                        choices=tuple(item["id"] for item in list_rulesets()))

    check = sub.add_parser("validate")
    check.add_argument("batch_id")
    check.add_argument("--request-id", default=None)

    for name in ("summary", "findings"):
        view = sub.add_parser(name)
        view.add_argument("run_id")
        if name == "findings":
            view.add_argument("--offset", type=int, default=0)
            view.add_argument("--status", choices=STATUSES)

    review = sub.add_parser("review")
    review.add_argument("finding_id")
    review.add_argument("--status", required=True, choices=STATUSES)
    review.add_argument("--reason", required=True)
    review.add_argument("--revision", type=int, required=True)
    review.add_argument("--request-id", required=True)
    review.add_argument("--confirm", action="store_true",
                        help="Explicitly approve this exact change; without this flag nothing is saved")

    export = sub.add_parser("export", help="Export findings, review history and summary; raw CSV is excluded")
    export.add_argument("run_id")
    export.add_argument("output_dir", type=Path)
    export.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()

    try:
        if args.command == "rulesets":
            print(json.dumps(list_rulesets(), indent=2, ensure_ascii=True))
            return 0

        store = Store(args.db)

        if args.command in ("demo", "demo-field"):
            ruleset_id = LEGACY_RULESET if args.command == "demo" else FIELD_RULESET
            batch_id = store.register(demo_bytes(ruleset_id), ruleset_id)
            result = store.validate_batch(batch_id, uuid.uuid4().hex)

        elif args.command == "import-csv":
            with args.path.open("rb") as source:
                data = source.read(MAX_BYTES + 1)
            result = {"batch_id": store.register(data, args.ruleset), "ruleset": args.ruleset}

        elif args.command == "validate":
            result = store.validate_batch(args.batch_id, args.request_id or uuid.uuid4().hex)

        elif args.command == "summary":
            result = store.summary(args.run_id)

        elif args.command == "findings":
            result = store.list_findings(args.run_id, status=args.status, offset=args.offset)

        elif args.command == "export":
            from fieldready.reporting import export_review_package
            result = export_review_package(
                store, args.run_id, args.output_dir, overwrite=args.overwrite
            )

        else:
            result = store.decide(
                args.finding_id, args.status, args.reason, args.revision,
                args.request_id, confirmed=args.confirm,
            )

        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"FieldReady error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
