"""Transactional local storage with immutable source/ruleset binding and review history."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fieldready.rule_engine import LEGACY_RULESET, read_for_ruleset, validate_for_ruleset

STATUSES = ("open", "follow_up", "confirmed", "dismissed")
_DB_VERSION = 2


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str, label: str, maximum: int = 128) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters.")


def _batch_id(source_sha256: str, ruleset_id: str) -> str:
    # Preserve legacy IDs exactly so existing M0 databases and evidence remain valid.
    if ruleset_id == LEGACY_RULESET:
        return source_sha256
    return hashlib.sha256((ruleset_id + "\0" + source_sha256).encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            self._initialise(db)

    @staticmethod
    def _initialise(db: sqlite3.Connection) -> None:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, 2):
            raise ValueError("Unsupported database version; do not overwrite it.")

        if version == 0:
            db.executescript(f"""
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    source_sha256 TEXT NOT NULL,
                    source BLOB NOT NULL,
                    row_count INTEGER NOT NULL,
                    ruleset_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL REFERENCES batches(id),
                    request_id TEXT NOT NULL UNIQUE,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    ordinal INTEGER NOT NULL,
                    evidence TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','follow_up','confirmed','dismissed')),
                    revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS review_events (
                    id INTEGER PRIMARY KEY,
                    finding_id TEXT NOT NULL REFERENCES findings(id),
                    request_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    previous_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                PRAGMA user_version = {_DB_VERSION};
            """)
            return

        if version == 1:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(batches)")}
            if "ruleset_id" not in columns:
                db.execute(
                    "ALTER TABLE batches ADD COLUMN ruleset_id TEXT NOT NULL "
                    f"DEFAULT '{LEGACY_RULESET}'"
                )
            db.execute(f"PRAGMA user_version = {_DB_VERSION}")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, data: bytes, ruleset_id: str = LEGACY_RULESET) -> str:
        rows = read_for_ruleset(data, ruleset_id)
        source_digest = hashlib.sha256(data).hexdigest()
        batch_id = _batch_id(source_digest, ruleset_id)
        with self.connection() as db:
            db.execute(
                """INSERT OR IGNORE INTO batches
                   (id,source_sha256,source,row_count,ruleset_id,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (batch_id, source_digest, data, len(rows), ruleset_id, _now()),
            )
            stored = db.execute(
                "SELECT source_sha256,ruleset_id FROM batches WHERE id=?", (batch_id,)
            ).fetchone()
            if not stored or stored["source_sha256"] != source_digest or stored["ruleset_id"] != ruleset_id:
                raise ValueError("Stored batch identity conflict.")
        return batch_id

    def batch_info(self, batch_id: str) -> dict:
        with self.connection() as db:
            row = db.execute(
                "SELECT id,source_sha256,row_count,ruleset_id,created_at FROM batches WHERE id=?",
                (batch_id,),
            ).fetchone()
        if not row:
            raise ValueError("Unknown batch_id.")
        return dict(row)

    def validate_batch(self, batch_id: str, request_id: str) -> dict:
        _text(batch_id, "batch_id")
        _text(request_id, "request_id")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM runs WHERE request_id=?", (request_id,)).fetchone()
            if existing:
                if existing["batch_id"] != batch_id:
                    raise ValueError("request_id is already bound to a different batch.")
                return self._run(existing)
            batch = db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
            if not batch:
                raise ValueError("Unknown batch_id; import the CSV with the trusted control surface first.")
            if hashlib.sha256(batch["source"]).hexdigest() != batch["source_sha256"]:
                raise ValueError("Stored source failed its integrity check.")

            result = validate_for_ruleset(batch["source"], batch["ruleset_id"])
            run_id = uuid.uuid4().hex
            db.execute(
                "INSERT INTO runs(id,batch_id,request_id,result,created_at) VALUES (?,?,?,?,?)",
                (run_id, batch_id, request_id, _json(result), _now()),
            )
            for ordinal, item in enumerate(result["findings"], start=1):
                db.execute(
                    "INSERT INTO findings(id,run_id,ordinal,evidence) VALUES (?,?,?,?)",
                    (f"{run_id}:{ordinal}", run_id, ordinal, _json(item)),
                )
            return {"run_id": run_id, "batch_id": batch_id, **result}

    @staticmethod
    def _run(row: sqlite3.Row) -> dict:
        return {"run_id": row["id"], "batch_id": row["batch_id"], **json.loads(row["result"])}

    def get_run(self, run_id: str) -> dict:
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                raise ValueError("Unknown run_id.")
            return self._run(row)

    def list_findings(self, run_id: str, status: str | None = None,
                      limit: int = 50, offset: int = 0) -> dict:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100.")
        if type(offset) is not int or offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        if status is not None and status not in STATUSES:
            raise ValueError("Unknown review status.")
        self.get_run(run_id)
        clause = "run_id=?" + (" AND status=?" if status is not None else "")
        params = (run_id, status) if status is not None else (run_id,)
        with self.connection() as db:
            total = db.execute(f"SELECT COUNT(*) FROM findings WHERE {clause}", params).fetchone()[0]
            rows = db.execute(
                f"SELECT * FROM findings WHERE {clause} ORDER BY ordinal LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
        items = [
            {
                "finding_id": row["id"],
                "status": row["status"],
                "revision": row["revision"],
                **json.loads(row["evidence"]),
            }
            for row in rows
        ]
        return {
            "run_id": run_id,
            "total_matching": total,
            "offset": offset,
            "items": items,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
        }

    def all_findings(self, run_id: str) -> list[dict]:
        items: list[dict] = []
        offset = 0
        while True:
            page = self.list_findings(run_id, limit=100, offset=offset)
            items.extend(page["items"])
            if page["next_offset"] is None:
                return items
            offset = page["next_offset"]

    def summary(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        with self.connection() as db:
            counts = {
                row["status"]: row["n"]
                for row in db.execute(
                    "SELECT status,COUNT(*) AS n FROM findings WHERE run_id=? GROUP BY status",
                    (run_id,),
                )
            }
        return {key: value for key, value in run.items() if key != "findings"} | {
            "review_counts": {status: counts.get(status, 0) for status in STATUSES},
            "unresolved_findings": counts.get("open", 0) + counts.get("follow_up", 0),
        }

    def review_history(self, run_id: str) -> list[dict]:
        self.get_run(run_id)
        with self.connection() as db:
            rows = db.execute(
                """SELECT e.id,e.finding_id,e.request_id,e.payload,e.previous_status,
                          e.new_status,e.revision,e.created_at,f.evidence
                   FROM review_events e
                   JOIN findings f ON f.id=e.finding_id
                   WHERE f.run_id=?
                   ORDER BY e.id""",
                (run_id,),
            ).fetchall()
        result = []
        for row in rows:
            payload = json.loads(row["payload"])
            evidence = json.loads(row["evidence"])
            result.append({
                "event_id": row["id"],
                "finding_id": row["finding_id"],
                "request_id": row["request_id"],
                "row_number": evidence.get("row_number"),
                "record_id": evidence.get("record_id", ""),
                "rule_id": evidence.get("rule_id", ""),
                "previous_status": row["previous_status"],
                "new_status": row["new_status"],
                "revision": row["revision"],
                "reason": payload.get("reason", ""),
                "created_at": row["created_at"],
            })
        return result

    def decide(self, finding_id: str, status: str, reason: str, expected_revision: int,
               request_id: str, *, confirmed: bool = False) -> dict:
        """Trusted local control surface only. Deliberately not an MCP tool."""
        if confirmed is not True:
            raise ValueError("Explicit supervisor confirmation is required.")
        if status not in STATUSES:
            raise ValueError("Unknown review status.")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("expected_revision must be a non-negative integer.")
        _text(finding_id, "finding_id")
        _text(request_id, "request_id")
        _text(reason, "reason", 500)
        payload = _json({
            "finding_id": finding_id,
            "status": status,
            "reason": reason,
            "expected_revision": expected_revision,
        })
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM review_events WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old["payload"] != payload:
                    raise ValueError("request_id cannot be reused for a different decision.")
                return dict(old)
            row = db.execute("SELECT * FROM findings WHERE id=?", (finding_id,)).fetchone()
            if not row:
                raise ValueError("Unknown finding_id.")
            if row["revision"] != expected_revision:
                raise ValueError("Stale decision: reload the finding before confirming.")
            db.execute(
                "UPDATE findings SET status=?,revision=revision+1 WHERE id=?",
                (status, finding_id),
            )
            event = db.execute(
                """INSERT INTO review_events
                   (finding_id,request_id,payload,previous_status,new_status,revision,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    finding_id, request_id, payload, row["status"], status,
                    expected_revision + 1, _now(),
                ),
            )
            return dict(
                db.execute("SELECT * FROM review_events WHERE id=?", (event.lastrowid,)).fetchone()
            )
