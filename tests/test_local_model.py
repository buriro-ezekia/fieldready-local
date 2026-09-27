"""Mocked Ollama contracts; these tests never claim actual model inference."""
import json
import unittest
from unittest.mock import patch

from fieldready.local_model import INTENT_FORMAT, LocalExplainer, grounded_text, safe_model_name
from fieldready.mcp_client import MCPGateway


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.client = LocalExplainer("fixture:small")
        self.summary = dict(row_count=8, finding_count=6, affected_rows=6, unresolved_findings=6)
        self.finding = dict(row_number=2, rule_id="component_total", field="household_size", severity="high",
                            observed="5", expected="4", status="open", finding_id="abc:1", record_id="DO_NOT_SEND")
        self.calls = []
        self.responses = [{"models": [{"name": "fixture:small", "digest": "fixture-digest"}]},
                          {"model_info": {"general.architecture": "fixture"}},
                          {"done": True, "message": {"content": json.dumps({"intent": "in_scope"})}}]

    def fake(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.responses.pop(0)

    def execute(self, question="Why flagged?"):
        with patch.object(self.client, "_request", side_effect=self.fake):
            return self.client.explain(self.summary, self.finding, question)

    def test_mock_contract_and_no_tool_access(self):
        result = self.execute()
        self.assertEqual(result["digest"], "fixture-digest")
        self.assertEqual(result["intent"], "in_scope")
        self.assertEqual(result["rule_id"], "component_total")
        self.assertEqual(result["record_ordinal"], 2)
        request = self.calls[-1][2]
        self.assertFalse(request["stream"])
        self.assertEqual(request["format"], INTENT_FORMAT)
        self.assertNotIn("tools", request)
        self.assertNotIn("DO_NOT_SEND", str(request))
        self.assertNotIn("component_total", str(request["messages"]))
        self.assertIn("Rule component_total", result["text"])
        self.assertIn("record ordinal 2", result["text"])
        self.assertIn("recorded as 5", result["text"])
        self.assertIn("validated component total is 4", result["text"])

    def test_model_cannot_inject_prose_field(self):
        self.responses[2]["message"]["content"] = json.dumps({
            "intent": "in_scope",
            "explanation": "sampling bias caused this",
        })
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_out_of_scope_gets_deterministic_decline(self):
        self.responses[2]["message"]["content"] = json.dumps({"intent": "out_of_scope"})
        result = self.execute("Write a poem.")
        self.assertEqual(result["intent"], "out_of_scope")
        self.assertIn("outside this finding-review assistant's scope", result["text"])
        self.assertNotIn("poem", result["text"].lower())

    def test_grounded_component_total(self):
        text = grounded_text(self.finding)
        self.assertIn("component_total", text)
        self.assertIn("record ordinal 2", text)
        self.assertIn("household_size is recorded as 5", text)
        self.assertIn("validated component total is 4", text)

    def test_grounded_duplicate_id(self):
        finding = dict(self.finding, row_number=3, rule_id="duplicate_id", field="record_id",
                       observed="0003", expected="A unique identifier")
        text = grounded_text(finding)
        self.assertIn("0003", text)
        self.assertIn("occurs more than once", text)

    def test_grounded_missing_id(self):
        finding = dict(self.finding, row_number=5, rule_id="missing_id", field="record_id",
                       observed="", expected="A non-empty identifier")
        text = grounded_text(finding)
        self.assertIn("(missing)", text)
        self.assertIn("non-empty identifier", text)

    def test_grounded_missing_count(self):
        finding = dict(self.finding, row_number=6, rule_id="missing_count", field="adults",
                       observed="", expected="An integer from 0 to 100")
        text = grounded_text(finding)
        self.assertIn("adults is (missing)", text)
        self.assertIn("integer from 0 to 100", text)

    def test_grounded_invalid_count(self):
        finding = dict(self.finding, row_number=7, rule_id="invalid_count", field="adults",
                       observed="-1", expected="An integer from 0 to 100")
        text = grounded_text(finding)
        self.assertIn("adults is recorded as -1", text)
        self.assertIn("integer from 0 to 100", text)

    def test_unknown_rule_uses_generic_evidence_only_template(self):
        finding = dict(self.finding, rule_id="future_rule", field="x", observed="A", expected="B")
        text = grounded_text(finding)
        self.assertEqual(
            text,
            "Rule future_rule · record ordinal 2. The finding concerns x: observed A; expected B. "
            "Verification: check the displayed evidence against the source before recording a review outcome."
        )

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

    def test_unsupported_intent_rejected(self):
        self.responses[2]["message"]["content"] = json.dumps({"intent": "maybe"})
        with self.assertRaises(RuntimeError):
            self.execute()

    def test_oversized_evidence_rejected(self):
        self.finding["observed"] = "x" * 201
        with self.assertRaises(ValueError):
            self.execute()

    def test_incomplete_evidence_rejected(self):
        del self.finding["field"]
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
