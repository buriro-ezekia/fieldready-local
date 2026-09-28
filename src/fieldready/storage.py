"""Transactional local storage, immutable evidence snapshots and explicit reviews."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fieldready.rules import read_csv, validate

STATUSES = ("open", "follow_up", "confirmed", "dismissed")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str, label: str, maximum: int = 128) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters.")


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Unsupported database version; do not overwrite it.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL,
                    source BLOB NOT NULL, row_count INTEGER NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
                    request_id TEXT NOT NULL UNIQUE, result TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    ordinal INTEGER NOT NULL, evidence TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','follow_up','confirmed','dismissed')),
                    revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS review_events (
                    id INTEGER PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id),
                    request_id TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
                    previous_status TEXT NOT NULL, new_status TEXT NOT NULL,
                    revision INTEGER NOT NULL, created_at TEXT NOT NULL
                );
                PRAGMA user_version = 1;
            """)

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

    def register(self, data: bytes) -> str:
        rows = read_csv(data)
        digest = hashlib.sha256(data).hexdigest()
        with self.connection() as db:
            db.execute("INSERT OR IGNORE INTO batches VALUES (?,?,?,?,?)",
                       (digest, digest, data, len(rows), _now()))
        return digest

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
                raise ValueError("Unknown batch_id; import the CSV with the trusted CLI first.")
            if hashlib.sha256(batch["source"]).hexdigest() != batch["source_sha256"]:
                raise ValueError("Stored source failed its integrity check.")
            result = validate(batch["source"])
            run_id = uuid.uuid4().hex
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?)",
                       (run_id, batch_id, request_id, _json(result), _now()))
            for ordinal, item in enumerate(result["findings"], start=1):
                db.execute("INSERT INTO findings(id,run_id,ordinal,evidence) VALUES (?,?,?,?)",
                           (f"{run_id}:{ordinal}", run_id, ordinal, _json(item)))
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
            rows = db.execute(f"SELECT * FROM findings WHERE {clause} ORDER BY ordinal LIMIT ? OFFSET ?",
                              (*params, limit, offset)).fetchall()
        items = [{"finding_id": row["id"], "status": row["status"], "revision": row["revision"],
                  **json.loads(row["evidence"])} for row in rows]
        return {"run_id": run_id, "total_matching": total, "offset": offset, "items": items,
                "next_offset": offset + len(items) if offset + len(items) < total else None}

    def summary(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        with self.connection() as db:
            counts = {row["status"]: row["n"] for row in db.execute(
                "SELECT status,COUNT(*) AS n FROM findings WHERE run_id=? GROUP BY status", (run_id,))}
        return {key: value for key, value in run.items() if key != "findings"} | {
            "review_counts": {status: counts.get(status, 0) for status in STATUSES},
            "unresolved_findings": counts.get("open", 0) + counts.get("follow_up", 0),
        }

    def decide(self, finding_id: str, status: str, reason: str, expected_revision: int,
               request_id: str, *, confirmed: bool = False) -> dict:
        """Trusted local CLI only. This method is deliberately not an MCP tool."""
        if confirmed is not True:
            raise ValueError("Explicit supervisor confirmation is required.")
        if status not in STATUSES:
            raise ValueError("Unknown review status.")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("expected_revision must be a non-negative integer.")
        _text(finding_id, "finding_id")
        _text(request_id, "request_id")
        _text(reason, "reason", 500)
        payload = _json({"finding_id": finding_id, "status": status, "reason": reason,
                         "expected_revision": expected_revision})
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
            db.execute("UPDATE findings SET status=?,revision=revision+1 WHERE id=?",
                       (status, finding_id))
            event = db.execute("""INSERT INTO review_events
                (finding_id,request_id,payload,previous_status,new_status,revision,created_at)
                VALUES (?,?,?,?,?,?,?)""", (finding_id, request_id, payload, row["status"], status,
                                           expected_revision + 1, _now()))
            return dict(db.execute("SELECT * FROM review_events WHERE id=?", (event.lastrowid,)).fetchone())
