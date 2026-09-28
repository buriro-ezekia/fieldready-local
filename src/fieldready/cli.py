"""Local control surface; review changes are never available as model tools."""

import argparse
import json
import os
import sqlite3
import sys
import uuid
from importlib.resources import files
from pathlib import Path

from fieldready.storage import STATUSES, Store


def default_db() -> Path:
    home = Path(os.environ.get("FIELDREADY_HOME", str(Path.home() / ".fieldready-local")))
    return home / "fieldready.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description="FieldReady Local — synthetic survey-review prototype")
    parser.add_argument("--db", type=Path, default=default_db())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Import and validate the bundled synthetic batch")
    ingest = sub.add_parser("import-csv", help="Import a local file; do not use confidential data yet")
    ingest.add_argument("path", type=Path)
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
    args = parser.parse_args()
    try:
        store = Store(args.db)
        if args.command == "demo":
            data = files("fieldready").joinpath("data/survey.csv").read_bytes()
            batch_id = store.register(data)
            result = store.validate_batch(batch_id, uuid.uuid4().hex)
        elif args.command == "import-csv":
            from fieldready.rules import MAX_BYTES
            with args.path.open("rb") as source:
                data = source.read(MAX_BYTES + 1)
            result = {"batch_id": store.register(data)}
        elif args.command == "validate":
            result = store.validate_batch(args.batch_id, args.request_id or uuid.uuid4().hex)
        elif args.command == "summary":
            result = store.summary(args.run_id)
        elif args.command == "findings":
            result = store.list_findings(args.run_id, status=args.status, offset=args.offset)
        else:
            result = store.decide(args.finding_id, args.status, args.reason, args.revision,
                                  args.request_id, confirmed=args.confirm)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"FieldReady error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
