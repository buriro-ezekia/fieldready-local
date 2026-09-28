"""Static checks for the production scope/focus evaluation design."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import evaluate_intent  # noqa: E402
from fieldready.local_model import scope_guard  # noqa: E402


class EvaluationDesignTests(unittest.TestCase):
    def test_cases_are_balanced_unique_and_valid(self):
        cases = json.loads((ROOT / "evaluations" / "intent_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 16)
        self.assertEqual(len({case["id"] for case in cases}), 16)
        counts = {"in_scope": 0, "out_of_scope": 0}
        valid_focus = {"reason", "verification", "evidence", "review_guidance", "combined"}
        for case in cases:
            self.assertIn(case["expected"], counts)
            self.assertTrue(case["question"].strip())
            counts[case["expected"]] += 1
            if case["expected"] == "in_scope":
                self.assertIn(case["expected_focus"], valid_focus)
            else:
                self.assertIsNone(case["expected_focus"])
        self.assertEqual(counts, {"in_scope": 8, "out_of_scope": 8})

    def test_production_scope_guard_routes_benchmark_cases(self):
        cases = json.loads((ROOT / "evaluations" / "intent_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(scope_guard(case["question"]), case["expected"])

    def test_percentile_uses_nearest_rank(self):
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(evaluate_intent.percentile(values, 0.50), 2.0)
        self.assertEqual(evaluate_intent.percentile(values, 0.95), 4.0)


if __name__ == "__main__":
    unittest.main()
