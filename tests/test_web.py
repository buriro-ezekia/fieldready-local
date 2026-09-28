"""ASGI/browser-surface unit checks with a labelled MCP stub, not protocol execution."""
import json
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path

from fieldready.rule_engine import FIELD_RULESET, demo_bytes
from fieldready.storage import Store
from fieldready.web_app import WebApp


class StubGateway:
    """Test-only substitute; the production launcher always constructs MCPGateway."""
    def __init__(self, db):
        self.store = Store(db)
        self.calls = []

    async def call(self, name, args):
        self.calls.append(name)
        if name == "validate_batch":
            return self.store.summary(self.store.validate_batch(**args)["run_id"])
        if name == "get_review_summary":
            return self.store.summary(**args)
        if name == "list_findings":
            return self.store.list_findings(**args)
        raise AssertionError("Forbidden tool: " + name)


class WebTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "test.sqlite3"
        self.gateway = StubGateway(self.db)
        self.token = "a" * 40
        self.app = WebApp(self.db, self.gateway, self.token, 8501)

    async def request(self, path, body=None, *, auth=True, host=b"127.0.0.1:8501", extra=(), raw=None):
        headers = [(b"host", host), (b"content-type", b"application/json")]
        if auth:
            headers.append((b"authorization", ("Bearer " + self.token).encode()))
        headers.extend(extra)
        events = []
        async def receive():
            return {"type": "http.request", "body": raw if raw is not None else json.dumps(body).encode()}
        async def send(event):
            events.append(event)
        await self.app({"type": "http", "path": path, "method": "POST" if body is not None or raw is not None else "GET", "headers": headers}, receive, send)
        data = events[1]["body"]
        if path not in ("/", "/app.js", "/app.css"):
            data = json.loads(data)
        return events[0]["status"], data, dict(events[0]["headers"])

    async def demo(self):
        status, result, _ = await self.request("/api/demo", {"request_id": "demo"})
        self.assertEqual(status, 200)
        return result["run_id"]

    async def decision(self, confirmed=True):
        run = await self.demo()
        return {"finding_id": run + ":1", "status": "confirmed", "reason": "Checked synthetic fixture",
                "expected_revision": 0, "request_id": "decision", "confirmed": confirmed}

    async def test_assets_public_but_data_authenticated(self):
        self.assertEqual((await self.request("/", auth=False))[0], 200)
        self.assertEqual((await self.request("/api/info", auth=False))[0], 401)

    async def test_reject_foreign_host(self):
        self.assertEqual((await self.request("/api/info", host=b"attacker.test:8501"))[0], 421)

    async def test_reject_foreign_origin(self):
        self.assertEqual((await self.request("/api/info", extra=[(b"origin", b"https://evil.test")]))[0], 403)

    async def test_accept_exact_origin(self):
        self.assertEqual((await self.request("/api/info", extra=[(b"origin", b"http://127.0.0.1:8501")]))[0], 200)

    async def test_reject_duplicate_auth(self):
        self.assertEqual((await self.request("/api/info", extra=[(b"authorization", b"Bearer wrong")]))[0], 400)

    async def test_security_headers(self):
        _, _, headers = await self.request("/")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertIn(b"frame-ancestors 'none'", headers[b"content-security-policy"])
        self.assertEqual(headers[b"referrer-policy"], b"no-referrer")

    async def test_static_path_traversal_not_served(self):
        self.assertEqual((await self.request("/../storage.py"))[0], 404)

    async def test_malformed_json_rejected(self):
        self.assertEqual((await self.request("/api/demo", raw=b"{"))[0], 400)

    async def test_array_json_rejected(self):
        self.assertEqual((await self.request("/api/demo", raw=b"[]"))[0], 400)

    async def test_oversized_request_rejected(self):
        self.assertEqual((await self.request("/api/import", raw=b"x" * 2_097_153))[0], 413)

    async def test_extra_action_field_rejected(self):
        self.assertEqual((await self.request("/api/demo", {"request_id": "x", "path": "/etc/passwd"}))[0], 400)

    async def test_import_enforces_questionnaire(self):
        self.assertEqual((await self.request("/api/import", {"request_id": "x", "csv": "name\nAlice\n"}))[0], 400)

    async def test_validation_goes_through_gateway(self):
        run = await self.demo()
        status, data, _ = await self.request("/api/run", {"run_id": run})
        self.assertEqual(status, 200)
        self.assertEqual(data["summary"]["finding_count"], 6)
        self.assertEqual(len(data["page"]["items"]), 6)
        self.assertEqual(self.gateway.calls, ["validate_batch", "get_review_summary", "list_findings"])

    async def test_no_direct_validation_fallback(self):
        async def broken(*args):
            raise RuntimeError("MCP unavailable")
        self.gateway.call = broken
        self.assertEqual((await self.request("/api/demo", {"request_id": "x"}))[0], 503)
        with self.app.store.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 0)

    async def test_unconfirmed_write_rejected(self):
        body = await self.decision(False)
        self.assertEqual((await self.request("/api/decision", body))[0], 400)
        self.assertEqual(self.app.store.summary(body["finding_id"].split(":")[0])["unresolved_findings"], 6)

    async def test_confirmed_write_and_replay(self):
        body = await self.decision()
        first = await self.request("/api/decision", body)
        second = await self.request("/api/decision", body)
        self.assertEqual(first[0], 200)
        self.assertEqual(first[1], second[1])
        self.assertEqual(self.gateway.calls, ["validate_batch"])

    async def test_stale_decision_rejected(self):
        body = await self.decision()
        await self.request("/api/decision", body)
        body["request_id"] = "different"
        self.assertEqual((await self.request("/api/decision", body))[0], 400)

    async def test_source_bytes_unchanged_and_state_persisted(self):
        body = await self.decision()
        await self.request("/api/decision", body)
        self.app = WebApp(self.db, self.gateway, self.token, 8501)
        run = body["finding_id"].split(":")[0]
        _, data, _ = await self.request("/api/run", {"run_id": run})
        self.assertEqual(data["summary"]["unresolved_findings"], 5)
        with self.app.store.connection() as db:
            self.assertEqual(db.execute("SELECT source FROM batches").fetchone()[0], files("fieldready").joinpath("data/survey.csv").read_bytes())

    async def test_saved_runs_list(self):
        run = await self.demo()
        _, data, _ = await self.request("/api/info")
        self.assertEqual(data["runs"][0]["id"], run)
        self.assertIsNone(data["model"])

    async def test_model_disabled_fails_visibly(self):
        run = await self.demo()
        status, data, _ = await self.request("/api/explain", {"run_id": run, "finding_id": run+":1", "question": "Why?"})
        self.assertEqual(status, 400)
        self.assertIn("disabled", data["error"])

    async def test_selected_evidence_passed_to_model_no_write(self):
        class StubExplainer:
            model = "test-only"
            def explain(self, summary, finding, question):
                return {"rule": finding["rule_id"], "count": summary["finding_count"], "text": "TEST STUB"}
        self.app.explainer = StubExplainer()
        run = await self.demo()
        status, result, _ = await self.request("/api/explain", {"run_id": run, "finding_id": run+":1", "question": "Why?"})
        self.assertEqual(status, 200)
        self.assertEqual(result["rule"], "component_total")
        self.assertEqual(self.app.store.summary(run)["unresolved_findings"], 6)

    async def test_ai_request_cannot_add_write_fields(self):
        run = await self.demo()
        self.assertEqual((await self.request("/api/explain", {"run_id": run, "finding_id": run+":1", "question": "Why?", "confirmed": True}))[0], 400)

    async def test_filter_and_offset(self):
        body = await self.decision()
        await self.request("/api/decision", body)
        _, data, _ = await self.request("/api/run", {"run_id": body["finding_id"].split(":")[0], "status": "open", "offset": 1})
        self.assertEqual(data["page"]["total_matching"], 5)
        self.assertEqual(len(data["page"]["items"]), 4)

    async def test_field_demo_uses_gateway_and_rich_ruleset(self):
        status, result, _ = await self.request("/api/demo-field", {"request_id": "rich-demo"})
        self.assertEqual(status, 200)
        self.assertEqual(result["finding_count"], 17)
        self.assertEqual(result["affected_rows"], 13)
        self.assertEqual(result["ruleset"], FIELD_RULESET)
        self.assertEqual(result["severity_counts"], {"critical": 3, "high": 9, "medium": 5})
        self.assertEqual(self.gateway.calls, ["validate_batch"])

    async def test_ruleset_aware_import_is_bound_to_selected_version(self):
        status, result, _ = await self.request("/api/import", {
            "request_id": "rich-import",
            "ruleset_id": FIELD_RULESET,
            "csv": demo_bytes(FIELD_RULESET).decode("utf-8"),
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["ruleset"], FIELD_RULESET)
        with self.app.store.connection() as db:
            stored = db.execute(
                "SELECT ruleset_id FROM batches WHERE id=?", (result["batch_id"],)
            ).fetchone()
        self.assertEqual(stored["ruleset_id"], FIELD_RULESET)

    async def test_info_exposes_rulesets_and_saved_run_ruleset(self):
        status, result, _ = await self.request("/api/demo-field", {"request_id": "catalog-demo"})
        self.assertEqual(status, 200)
        _, info, _ = await self.request("/api/info")
        rulesets = {item["id"] for item in info["rulesets"]}
        self.assertIn(FIELD_RULESET, rulesets)
        self.assertEqual(info["runs"][0]["id"], result["run_id"])
        self.assertEqual(info["runs"][0]["ruleset_id"], FIELD_RULESET)

    async def test_export_uses_fixed_local_directory_and_excludes_source(self):
        status, result, _ = await self.request("/api/demo-field", {"request_id": "export-demo"})
        self.assertEqual(status, 200)
        run_id = result["run_id"]
        status, exported, _ = await self.request("/api/export", {"run_id": run_id})
        self.assertEqual(status, 200)
        self.assertFalse(exported["source_csv_included"])
        output = Path(exported["output_dir"])
        self.assertEqual(output, self.db.parent / "exports" / run_id)
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"summary.md", "findings.csv", "review_history.csv", "manifest.json"},
        )
        denied = await self.request("/api/export", {
            "run_id": run_id,
            "output_dir": str(self.db.parent / "attacker-selected"),
        })
        self.assertEqual(denied[0], 400)

    async def test_dom_uses_text_not_untrusted_html(self):
        _, js, _ = await self.request("/app.js")
        self.assertNotIn(b"innerHTML", js)
        self.assertIn(b"textContent", js)
        self.assertIn(b"history.replaceState", js)

    def test_invalid_web_credential(self):
        with self.assertRaises(ValueError):
            WebApp(self.db, self.gateway, "short", 8501)
