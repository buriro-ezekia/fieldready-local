"""Versioned ruleset, migration and local report-package checks."""
import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fieldready.reporting import export_review_package
from fieldready.rule_engine import (
    FIELD_RULESET, LEGACY_RULESET, demo_bytes, list_rulesets, validate_for_ruleset,
)
from fieldready.storage import Store

RICH = demo_bytes(FIELD_RULESET)


class VersionedRuleTests(unittest.TestCase):
    def test_catalog_contains_legacy_and_field_rulesets(self):
        catalog = {item["id"]: item for item in list_rulesets()}
        self.assertIn(LEGACY_RULESET, catalog)
        self.assertIn(FIELD_RULESET, catalog)
        self.assertEqual(catalog[FIELD_RULESET]["version"], "1.0.0")
        self.assertFalse(catalog[FIELD_RULESET]["legacy"])

    def test_rich_demo_matches_independent_answer_key(self):
        result = validate_for_ruleset(RICH, FIELD_RULESET)
        self.assertEqual(result["ruleset"], FIELD_RULESET)
        self.assertEqual(result["ruleset_version"], "1.0.0")
        self.assertEqual(
            (result["row_count"], result["finding_count"], result["affected_rows"]),
            (14, 17, 13),
        )
        self.assertEqual(result["severity_counts"], {"critical": 3, "high": 9, "medium": 5})
        self.assertEqual(result["category_counts"], {
            "completeness": 4,
            "consistency": 2,
            "duration": 2,
            "geospatial": 2,
            "uniqueness": 2,
            "validity": 5,
        })
        self.assertEqual(result["check_evaluations"], {"evaluable": 80, "not_evaluable": 5})
        self.assertEqual(result["total_checks_not_evaluable"], [9, 11, 12, 14])

        expected = [
            (2, "household.component_total"),
            (3, "respondent_age.range"),
            (4, "interview.duration"),
            (5, "district.choice"),
            (6, "record_id.unique"),
            (7, "record_id.unique"),
            (7, "children_under5.le_children"),
            (8, "respondent_age.when_consent"),
            (8, "gps.accuracy"),
            (9, "children.required"),
            (10, "water_source.other_text"),
            (11, "record_id.required"),
            (12, "consent.choice"),
            (13, "respondent_age.range"),
            (13, "interview.duration"),
            (13, "gps.accuracy"),
            (14, "household_size.range"),
        ]
        self.assertEqual(
            [(item["row_number"], item["rule_id"]) for item in result["findings"]],
            expected,
        )

    def test_rich_finding_carries_deterministic_explanation_metadata(self):
        result = validate_for_ruleset(RICH, FIELD_RULESET)
        finding = next(item for item in result["findings"]
                       if item["rule_id"] == "gps.accuracy")
        self.assertEqual(finding["category"], "geospatial")
        self.assertEqual(finding["severity"], "medium")
        self.assertIn("GPS accuracy", finding["message"])
        self.assertIn("location", finding["verification"])

    def test_wrong_schema_is_rejected_before_storage(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "db.sqlite3")
            with self.assertRaises(ValueError):
                store.register(b"record_id,adults\nX,1\n", FIELD_RULESET)


class VersionedStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "review.sqlite3"
        self.store = Store(self.db)
        self.batch = self.store.register(RICH, FIELD_RULESET)
        self.run = self.store.validate_batch(self.batch, "rich-validation")

    def test_batch_is_bound_to_ruleset(self):
        info = self.store.batch_info(self.batch)
        self.assertEqual(info["ruleset_id"], FIELD_RULESET)
        self.assertEqual(info["row_count"], 14)
        self.assertEqual(self.run["ruleset"], FIELD_RULESET)
        self.assertNotEqual(self.batch, hashlib.sha256(RICH).hexdigest())

    def test_summary_and_findings_preserve_rich_metadata(self):
        summary = self.store.summary(self.run["run_id"])
        self.assertEqual(summary["severity_counts"]["critical"], 3)
        first = self.store.list_findings(self.run["run_id"])["items"][0]
        self.assertIn("category", first)
        self.assertIn("message", first)
        self.assertIn("verification", first)

    def test_review_history_and_export_package(self):
        finding = self.store.list_findings(self.run["run_id"])["items"][0]
        self.store.decide(
            finding["finding_id"], "confirmed", "Checked synthetic source evidence",
            0, "rich-review-1", confirmed=True,
        )
        history = self.store.review_history(self.run["run_id"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["reason"], "Checked synthetic source evidence")

        output = Path(self.tmp.name) / "package"
        result = export_review_package(self.store, self.run["run_id"], output)
        self.assertFalse(result["source_csv_included"])
        self.assertEqual(
            set(path.name for path in output.iterdir()),
            {"summary.md", "findings.csv", "review_history.csv", "manifest.json"},
        )

        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["source_csv_included"])
        self.assertEqual(manifest["ruleset"], FIELD_RULESET)
        self.assertEqual(manifest["finding_count"], 17)
        self.assertEqual(manifest["review_event_count"], 1)
        for name, metadata in manifest["files"].items():
            self.assertEqual(
                hashlib.sha256((output / name).read_bytes()).hexdigest(),
                metadata["sha256"],
            )

        summary_text = (output / "summary.md").read_text(encoding="utf-8")
        self.assertIn("field-survey-v1.0.0", summary_text)
        self.assertIn("The raw source CSV is not included", summary_text)

        findings_rows = list(csv.DictReader(io.StringIO(
            (output / "findings.csv").read_text(encoding="utf-8")
        )))
        self.assertEqual(len(findings_rows), 17)
        self.assertIn("severity", findings_rows[0])

        with self.assertRaises(ValueError):
            export_review_package(self.store, self.run["run_id"], output)
        export_review_package(self.store, self.run["run_id"], output, overwrite=True)

    def test_new_database_uses_schema_version_two(self):
        with self.store.connection() as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(batches)")}
        self.assertIn("ruleset_id", columns)


class MigrationTests(unittest.TestCase):
    def test_v1_database_migrates_with_legacy_ruleset_default(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.sqlite3"
            db = sqlite3.connect(path)
            db.executescript("""
                CREATE TABLE batches (
                    id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL,
                    source BLOB NOT NULL, row_count INTEGER NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE runs (
                    id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
                    request_id TEXT NOT NULL UNIQUE, result TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE findings (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    ordinal INTEGER NOT NULL, evidence TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE review_events (
                    id INTEGER PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id),
                    request_id TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
                    previous_status TEXT NOT NULL, new_status TEXT NOT NULL,
                    revision INTEGER NOT NULL, created_at TEXT NOT NULL
                );
                PRAGMA user_version = 1;
            """)
            source = demo_bytes(LEGACY_RULESET)
            digest = hashlib.sha256(source).hexdigest()
            db.execute(
                "INSERT INTO batches VALUES (?,?,?,?,?)",
                (digest, digest, source, 8, "2026-01-01T00:00:00+00:00"),
            )
            db.commit()
            db.close()

            store = Store(path)
            info = store.batch_info(digest)
            self.assertEqual(info["ruleset_id"], LEGACY_RULESET)
            with store.connection() as migrated:
                self.assertEqual(migrated.execute("PRAGMA user_version").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
