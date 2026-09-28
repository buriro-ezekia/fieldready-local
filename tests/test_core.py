"""Core tests use only the Python standard library and synthetic records."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from fieldready.rules import MAX_BYTES, read_csv, validate
from fieldready.storage import Store

DEMO = files("fieldready").joinpath("data/survey.csv").read_bytes()
HEADER = b"record_id,adults,children,household_size\n"
ROOT = Path(__file__).resolve().parents[1]


class RulesTests(unittest.TestCase):
    def test_demo_matches_independent_expected_findings(self):
        result = validate(DEMO)
        expected = [(2, "component_total"), (3, "duplicate_id"), (4, "duplicate_id"),
                    (5, "missing_id"), (6, "missing_count"), (7, "invalid_count")]
        self.assertEqual([(f["row_number"], f["rule_id"]) for f in result["findings"]], expected)
        self.assertEqual((result["row_count"], result["affected_rows"], result["finding_count"]), (8, 6, 6))
        self.assertEqual(result["total_checks_not_evaluable"], [6, 7])
        self.assertEqual(result["total_checks_evaluable"], 6)

    def test_clean_control_has_no_findings(self):
        self.assertEqual(validate(HEADER + b"0001,2,1,3\n")["finding_count"], 0)

    def test_leading_zero_identifiers_survive(self):
        self.assertEqual(read_csv(DEMO)[0]["record_id"], "0001")

    def test_bom_is_supported(self):
        self.assertEqual(read_csv(b"\xef\xbb\xbf" + DEMO), read_csv(DEMO))

    def test_multiple_findings_do_not_inflate_affected_rows(self):
        result = validate(HEADER + b",a,,2\n")
        self.assertEqual((result["finding_count"], result["affected_rows"]), (3, 1))
        self.assertEqual(result["total_checks_not_evaluable"], [1])

    def test_two_missing_ids_are_not_a_duplicate_id(self):
        result = validate(HEADER + b",0,0,0\n,0,0,0\n")
        self.assertEqual([f["rule_id"] for f in result["findings"]], ["missing_id", "missing_id"])

    def test_integer_boundaries_and_invalid_values(self):
        for value in ("-1", "1.5", "1e2", "NaN", "inf", "101", "1000"):
            with self.subTest(value=value):
                result = validate(HEADER + f"a,{value},0,1\n".encode())
                self.assertEqual(result["findings"][0]["rule_id"], "invalid_count")
                self.assertEqual(result["total_checks_not_evaluable"], [1])
        self.assertEqual(validate(HEADER + b"a,100,0,100\nb,0,0,0\n")["finding_count"], 0)

    def test_reject_malformed_headers_and_rows(self):
        for bad in (b"", HEADER, b"record_id,adults,adults,household_size\na,1,1,2\n",
                    HEADER + b"a,1,1\n", HEADER + b"a,1,1,2,extra\n",
                    HEADER + b'a,"unterminated,1,2\n', HEADER + b"a,1,\x00,2\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    read_csv(bad)

    def test_reject_non_utf8(self):
        with self.assertRaises(ValueError):
            read_csv(HEADER + b"\xff,1,1,2\n")

    def test_byte_and_row_limits(self):
        with self.assertRaises(ValueError):
            read_csv(b"x" * (MAX_BYTES + 1))
        with self.assertRaises(ValueError):
            read_csv(HEADER + b"a,1,1,2\n" * 2001)

    def test_source_bytes_unchanged(self):
        original = hashlib.sha256(DEMO).hexdigest()
        validate(DEMO)
        self.assertEqual(hashlib.sha256(DEMO).hexdigest(), original)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "review.sqlite3"
        self.store = Store(self.path)
        self.batch = self.store.register(DEMO)
        self.run = self.store.validate_batch(self.batch, "validation-1")
        self.finding = self.store.list_findings(self.run["run_id"])["items"][0]["finding_id"]

    def test_duplicate_import_is_idempotent(self):
        self.assertEqual(self.store.register(DEMO), self.batch)
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM batches").fetchone()[0], 1)

    def test_validation_request_is_idempotent(self):
        self.assertEqual(self.store.validate_batch(self.batch, "validation-1"), self.run)

    def test_validation_request_cannot_target_another_batch(self):
        other = self.store.register(HEADER + b"other,0,0,0\n")
        with self.assertRaisesRegex(ValueError, "different batch"):
            self.store.validate_batch(other, "validation-1")

    def test_unknown_batch_rejected_without_path_access(self):
        with self.assertRaisesRegex(ValueError, "Unknown batch"):
            self.store.validate_batch("../../private.csv", "new")

    def test_confirmation_is_required(self):
        for confirmation in (False, "true", 1):
            with self.subTest(confirmation=confirmation):
                with self.assertRaisesRegex(ValueError, "confirmation"):
                    self.store.decide(self.finding, "confirmed", "Reviewed", 0, "review-1",
                                      confirmed=confirmation)
        self.assertEqual(self.store.summary(self.run["run_id"])["unresolved_findings"], 6)

    def test_decision_persists_with_new_store(self):
        self.store.decide(self.finding, "confirmed", "Checked against synthetic answer key", 0,
                          "review-1", confirmed=True)
        reopened = Store(self.path)
        self.assertEqual(reopened.summary(self.run["run_id"])["unresolved_findings"], 5)
        self.assertEqual(reopened.list_findings(self.run["run_id"])["items"][0]["revision"], 1)

    def test_exact_replay_returns_same_event(self):
        args = (self.finding, "dismissed", "Documented exception", 0, "review-1")
        first = self.store.decide(*args, confirmed=True)
        self.assertEqual(self.store.decide(*args, confirmed=True), first)
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_events").fetchone()[0], 1)

    def test_reused_request_with_changed_payload_is_rejected(self):
        self.store.decide(self.finding, "confirmed", "Checked", 0, "review-1", confirmed=True)
        with self.assertRaisesRegex(ValueError, "different decision"):
            self.store.decide(self.finding, "dismissed", "Changed", 1, "review-1", confirmed=True)

    def test_stale_revision_is_rejected(self):
        self.store.decide(self.finding, "follow_up", "Recheck", 0, "review-1", confirmed=True)
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.store.decide(self.finding, "dismissed", "Old screen", 0, "review-2", confirmed=True)

    def test_revision_reason_and_status_validation(self):
        for status, reason, revision in (("invalid", "a", 0), ("open", " ", 0),
                                         ("open", "a", True), ("open", "a", -1),
                                         ("open", "a" * 501, 0)):
            with self.subTest(status=status, reason=reason, revision=revision):
                with self.assertRaises(ValueError):
                    self.store.decide(self.finding, status, reason, revision, "id", confirmed=True)

    def test_unknown_finding_does_not_write(self):
        with self.assertRaisesRegex(ValueError, "Unknown finding"):
            self.store.decide("unknown", "open", "Recheck", 0, "id", confirmed=True)

    def test_summary_counts_statuses_separately(self):
        self.store.decide(self.finding, "follow_up", "Recheck", 0, "r1", confirmed=True)
        summary = self.store.summary(self.run["run_id"])
        self.assertEqual(summary["review_counts"], {"open": 5, "follow_up": 1, "confirmed": 0, "dismissed": 0})
        self.assertEqual(summary["unresolved_findings"], 6)

    def test_pagination_and_filter(self):
        first = self.store.list_findings(self.run["run_id"], limit=2)
        second = self.store.list_findings(self.run["run_id"], limit=2, offset=first["next_offset"])
        self.assertEqual(first["total_matching"], 6)
        self.assertNotEqual(first["items"][0]["finding_id"], second["items"][0]["finding_id"])
        self.assertEqual(self.store.list_findings(self.run["run_id"], status="dismissed")["items"], [])

    def test_bad_page_and_unknown_run_rejected(self):
        for kwargs in ({"limit": 0}, {"limit": 101}, {"limit": True}, {"offset": -1},
                       {"status": "invalid"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    self.store.list_findings(self.run["run_id"], **kwargs)
        with self.assertRaises(ValueError):
            self.store.summary("unknown")

    def test_revalidation_does_not_copy_decisions(self):
        self.store.decide(self.finding, "confirmed", "Checked", 0, "r1", confirmed=True)
        newer = self.store.validate_batch(self.batch, "validation-2")
        self.assertNotEqual(newer["run_id"], self.run["run_id"])
        self.assertEqual(self.store.summary(newer["run_id"])["unresolved_findings"], 6)

    def test_stored_source_unchanged_after_review(self):
        self.store.decide(self.finding, "confirmed", "Checked", 0, "r1", confirmed=True)
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT source FROM batches WHERE id=?", (self.batch,)).fetchone()[0], DEMO)

    def test_stored_source_integrity_is_checked(self):
        with self.store.connection() as db:
            db.execute("UPDATE batches SET source=? WHERE id=?", (HEADER + b"x,1,1,2\n", self.batch))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.validate_batch(self.batch, "validation-2")

    def test_validation_transaction_rolls_back(self):
        with patch("fieldready.storage.validate", side_effect=ValueError("Injected failure")):
            with self.assertRaises(ValueError):
                self.store.validate_batch(self.batch, "failed-validation")
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)

    def test_unrecognised_db_version_rejected(self):
        with self.store.connection() as db:
            db.execute("PRAGMA user_version = 99")
        with self.assertRaises(ValueError):
            Store(self.path)

    def test_cli_decision_survives_separate_processes(self):
        script = str(ROOT / "scripts" / "fieldready.py")
        base = [sys.executable, script, "--db", str(self.path)]
        args = ["review", self.finding, "--status", "confirmed", "--reason", "Synthetic test",
                "--revision", "0", "--request-id", "cli-review"]
        denied = subprocess.run(base + args, capture_output=True, text=True, timeout=10)
        self.assertEqual(denied.returncode, 2)
        accepted = subprocess.run(base + args + ["--confirm"], capture_output=True, text=True, timeout=10)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        reopened = subprocess.run(base + ["summary", self.run["run_id"]], capture_output=True, text=True, timeout=10)
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        self.assertEqual(json.loads(reopened.stdout)["unresolved_findings"], 5)


if __name__ == "__main__":
    unittest.main()
