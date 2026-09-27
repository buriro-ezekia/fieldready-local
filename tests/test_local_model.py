"""Mocked Ollama contracts; these tests never claim actual model inference."""
import json
import unittest
from unittest.mock import patch

from fieldready.local_model import FORMAT, LocalExplainer, safe_model_name
from fieldready.mcp_client import MCPGateway


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.client = LocalExplainer("fixture:small")
        self.summary = dict(row_count=8, finding_count=6, affected_rows=6, unresolved_findings=6)
        self.finding = dict(row_number=2, rule_id="component_total", field="household_size", severity="high",
                            observed="5", expected="4", status="open", finding_id="abc:1", record_id="DO_NOT_SEND")
        self.calls = []
        self.payload = {
            "rule_id": "component_total",
            "record_ordinal": 2,
            "observed": "5",
            "expected": "4",
            "explanation": "The recorded household_size is 5 while the expected component total is 4.",
            "verification": "Check the adults and children values used to derive the expected total before deciding.",
        }
        self.responses = [{"models": [{"name": "fixture:small", "digest": "fixture-digest"}]},
                          {"model_info": {"general.architecture": "fixture"}},
                          {"done": True, "message": {"content": json.dumps(self.payload)}}]

    def fake(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.responses.pop(0)

    def execute(self):
        with patch.object(self.client, "_request", side_effect=self.fake):
            return self.client.explain(self.summary, self.finding, "Why flagged?")

    def test_mock_contract_and_no_tool_access(self):
        result = self.execute()
        self.assertEqual(result["digest"], "fixture-digest")
        self.assertEqual(result["rule_id"], "component_total")
        self.assertEqual(result["record_ordinal"], 2)
        request = self.calls[-1][2]
        self.assertFalse(request["stream"])
        self.assertEqual(request["format"], FORMAT)
        self.assertNotIn("tools", request)
        self.assertNotIn("DO_NOT_SEND", str(request))
        self.assertIn("component_total", str(request))
        self.assertIn("record ordinal 2", result["text"])

    def test_cloud_name_rejected(self):
        with self.assertRaises(ValueError):
            safe_model_name("example:cloud")

    def test_url_name_rejected(self):
        with self.assertRaises(ValueError):
            safe_model_name("https://remote/model")

    def test_remote_metadata_rejected(self):
        self.responses[1]["remote_host"] = "https://remote.test"
        with self.assertRaises(ValueError):
            self.execute()

    def test_missing_model_not_downloaded(self):
        self.responses[0] = {"models": []}
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(len(self.calls), 1)

    def test_tool_calls_not_executed(self):
        self.responses[2]["message"]["tool_calls"] = [{"function": {"name": "apply_decision"}}]
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_empty_answer_no_fallback(self):
        self.responses[2]["message"]["content"] = ""
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_incomplete_answer_rejected(self):
        self.responses[2]["done"] = False
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_non_json_answer_rejected(self):
        self.responses[2]["message"]["content"] = "plain text"
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_schema_key_mismatch_rejected(self):
        bad = dict(self.payload)
        bad["extra"] = "not allowed"
        self.responses[2]["message"]["content"] = json.dumps(bad)
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_changed_rule_id_rejected(self):
        bad = dict(self.payload, rule_id="other_rule")
        self.responses[2]["message"]["content"] = json.dumps(bad)
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_changed_record_ordinal_rejected(self):
        bad = dict(self.payload, record_ordinal=3)
        self.responses[2]["message"]["content"] = json.dumps(bad)
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_changed_observed_value_rejected(self):
        bad = dict(self.payload, observed="4")
        self.responses[2]["message"]["content"] = json.dumps(bad)
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_unsupported_speculation_rejected(self):
        bad = dict(self.payload, explanation="This may be caused by sampling bias.")
        self.responses[2]["message"]["content"] = json.dumps(bad)
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_oversized_evidence_rejected(self):
        self.finding["observed"] = "x" * 201
        with self.assertRaises(ValueError):
            self.execute()

    def test_question_limit(self):
        with self.assertRaises(ValueError):
            self.client.explain(self.summary, self.finding, "x" * 601)

    def test_invalid_local_port(self):
        with self.assertRaises(ValueError):
            LocalExplainer("fixture:small", 0)

    def test_mcp_write_tool_rejected_before_import(self):
        import asyncio
        gateway = MCPGateway(8000, "a" * 40)
        with self.assertRaises(ValueError):
            asyncio.run(gateway.call("apply_decision", {}))

    def test_invalid_mcp_token(self):
        with self.assertRaises(ValueError):
            MCPGateway(8000, "short")


if __name__ == "__main__":
    unittest.main()
