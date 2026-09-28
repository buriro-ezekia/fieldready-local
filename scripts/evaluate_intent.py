"""Evaluate the production deterministic-scope + local-focus router."""
import argparse
import json
import math
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

CASES_PATH = ROOT / "evaluations" / "intent_cases.json"


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:1.5b")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--min-focus-accuracy", type=float, default=0.75)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "intent-eval.json")
    args = parser.parse_args()

    if args.repeats < 1 or args.repeats > 10:
        parser.error("--repeats must be between 1 and 10.")
    if not 0 <= args.min_focus_accuracy <= 1:
        parser.error("--min-focus-accuracy must be between 0 and 1.")
    ollama = shutil.which("ollama")
    if not ollama:
        print("INTENT EVAL: FAIL — Ollama is not installed or not on PATH.", file=sys.stderr)
        return 2

    from check_model import ollama_service
    from fieldready.local_model import LocalExplainer, grounded_text

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        print("INTENT EVAL: FAIL — no evaluation cases.", file=sys.stderr)
        return 2

    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)):
        print("INTENT EVAL: FAIL — case IDs are not unique.", file=sys.stderr)
        return 2

    valid_focus = {"reason", "verification", "evidence", "review_guidance", "combined"}
    for case in cases:
        if case.get("expected") not in {"in_scope", "out_of_scope"}:
            print("INTENT EVAL: FAIL — malformed scope label: " + repr(case), file=sys.stderr)
            return 2
        if not isinstance(case.get("question"), str) or not case["question"].strip():
            print("INTENT EVAL: FAIL — malformed question: " + repr(case), file=sys.stderr)
            return 2
        focus = case.get("expected_focus")
        if case["expected"] == "in_scope" and focus not in valid_focus:
            print("INTENT EVAL: FAIL — missing/invalid focus label: " + repr(case), file=sys.stderr)
            return 2
        if case["expected"] == "out_of_scope" and focus is not None:
            print("INTENT EVAL: FAIL — out-of-scope case must have null focus.", file=sys.stderr)
            return 2

    summary = {"row_count": 8, "finding_count": 6, "affected_rows": 6, "unresolved_findings": 6}
    finding = {
        "finding_id": "0" * 32 + ":1",
        "row_number": 2,
        "rule_id": "component_total",
        "field": "household_size",
        "severity": "high",
        "observed": "5",
        "expected": "4",
        "status": "open",
    }
    expected_grounded = grounded_text(finding)
    results = []

    try:
        with ollama_service(ollama, 11435):
            explainer = LocalExplainer(args.model, 11435)
            for repeat in range(1, args.repeats + 1):
                for case in cases:
                    wall_started = time.monotonic()
                    try:
                        result = explainer.explain(summary, finding, case["question"])
                        predicted = result["intent"]
                        predicted_focus = result.get("focus")
                        routing_source = result["routing_source"]
                        model_invoked = bool(result["model_invoked"])
                        model_elapsed = float(result["elapsed_seconds"]) if model_invoked else None

                        if predicted == "in_scope" and result["text"] != expected_grounded:
                            raise RuntimeError("In-scope response was not deterministic grounded output.")
                        if result["finding_id"] != finding["finding_id"]:
                            raise RuntimeError("Evidence reference changed during evaluation.")

                        scope_correct = predicted == case["expected"]
                        focus_correct = (
                            predicted_focus == case["expected_focus"]
                            if case["expected"] == "in_scope"
                            else predicted_focus is None
                        )
                        expected_route = (
                            "local_model_focus"
                            if case["expected"] == "in_scope"
                            else "deterministic_scope_guard"
                        )
                        routing_correct = routing_source == expected_route
                        error = None
                    except Exception as exc:
                        predicted = "error"
                        predicted_focus = None
                        routing_source = "error"
                        model_invoked = False
                        model_elapsed = None
                        scope_correct = False
                        focus_correct = False
                        routing_correct = False
                        error = type(exc).__name__ + ": " + str(exc)

                    end_to_end = round(time.monotonic() - wall_started, 4)
                    item = {
                        "id": case["id"],
                        "repeat": repeat,
                        "expected": case["expected"],
                        "predicted": predicted,
                        "scope_correct": scope_correct,
                        "expected_focus": case["expected_focus"],
                        "predicted_focus": predicted_focus,
                        "focus_correct": focus_correct,
                        "routing_source": routing_source,
                        "routing_correct": routing_correct,
                        "model_invoked": model_invoked,
                        "model_elapsed_seconds": model_elapsed,
                        "end_to_end_elapsed_seconds": end_to_end,
                        "error": error,
                    }
                    results.append(item)
                    pass_scope = scope_correct and routing_correct
                    focus_note = (
                        f"; focus {case['expected_focus']} -> {predicted_focus}"
                        if case["expected"] == "in_scope"
                        else ""
                    )
                    label = "PASS" if pass_scope else "MISS"
                    print(
                        f"{case['id']} repeat {repeat}: {case['expected']} -> {predicted} "
                        f"via {routing_source} [{label}]{focus_note}"
                    )
    except (OSError, RuntimeError, ValueError) as exc:
        print("INTENT EVAL: FAIL — " + str(exc), file=sys.stderr)
        return 2

    total = len(results)
    errors = sum(item["predicted"] == "error" for item in results)
    scope_correct_n = sum(item["scope_correct"] for item in results)
    scope_accuracy = scope_correct_n / total
    routing_correct_n = sum(item["routing_correct"] for item in results)
    routing_accuracy = routing_correct_n / total

    class_recall = {}
    for label in ("in_scope", "out_of_scope"):
        subset = [item for item in results if item["expected"] == label]
        class_recall[label] = sum(item["scope_correct"] for item in subset) / len(subset)

    focus_items = [item for item in results if item["expected"] == "in_scope"]
    focus_correct_n = sum(item["focus_correct"] for item in focus_items)
    focus_accuracy = focus_correct_n / len(focus_items)

    model_latencies = [
        item["model_elapsed_seconds"] for item in results
        if item["model_elapsed_seconds"] is not None
    ]
    end_to_end_latencies = [item["end_to_end_elapsed_seconds"] for item in results]

    scope_confusion = Counter((item["expected"], item["predicted"]) for item in results)
    focus_confusion = Counter(
        (item["expected_focus"], item["predicted_focus"])
        for item in focus_items
    )
    per_case_scope = defaultdict(list)
    per_case_focus = defaultdict(list)
    for item in results:
        per_case_scope[item["id"]].append(item["scope_correct"])
        if item["expected"] == "in_scope":
            per_case_focus[item["id"]].append(item["focus_correct"])

    expected_model_invocations = sum(
        case["expected"] == "in_scope" for case in cases
    ) * args.repeats
    expected_guarded = sum(
        case["expected"] == "out_of_scope" for case in cases
    ) * args.repeats

    report = {
        "model": args.model,
        "architecture": "deterministic_scope_plus_local_focus",
        "cases": len(cases),
        "repeats": args.repeats,
        "evaluations": total,
        "scope": {
            "correct": scope_correct_n,
            "accuracy": round(scope_accuracy, 4),
            "class_recall": {k: round(v, 4) for k, v in class_recall.items()},
            "confusion": {
                f"{expected}->{predicted}": count
                for (expected, predicted), count in sorted(scope_confusion.items())
            },
        },
        "routing": {
            "correct": routing_correct_n,
            "accuracy": round(routing_accuracy, 4),
            "model_invocations": sum(item["model_invoked"] for item in results),
            "expected_model_invocations": expected_model_invocations,
            "guarded_requests": sum(
                item["routing_source"] == "deterministic_scope_guard" for item in results
            ),
            "expected_guarded_requests": expected_guarded,
        },
        "focus": {
            "evaluations": len(focus_items),
            "correct": focus_correct_n,
            "accuracy": round(focus_accuracy, 4),
            "minimum_required_accuracy": args.min_focus_accuracy,
            "confusion": {
                f"{expected}->{predicted}": count
                for (expected, predicted), count in sorted(focus_confusion.items())
            },
        },
        "model_latency_seconds": {
            "n": len(model_latencies),
            "mean": round(statistics.mean(model_latencies), 3) if model_latencies else None,
            "median": round(statistics.median(model_latencies), 3) if model_latencies else None,
            "p95": round(percentile(model_latencies, 0.95), 3) if model_latencies else None,
            "min": round(min(model_latencies), 3) if model_latencies else None,
            "max": round(max(model_latencies), 3) if model_latencies else None,
        },
        "end_to_end_latency_seconds": {
            "n": len(end_to_end_latencies),
            "mean": round(statistics.mean(end_to_end_latencies), 3),
            "median": round(statistics.median(end_to_end_latencies), 3),
            "p95": round(percentile(end_to_end_latencies, 0.95), 3),
            "min": round(min(end_to_end_latencies), 4),
            "max": round(max(end_to_end_latencies), 3),
        },
        "per_case_scope_accuracy": {
            key: round(sum(values) / len(values), 4)
            for key, values in sorted(per_case_scope.items())
        },
        "per_case_focus_accuracy": {
            key: round(sum(values) / len(values), 4)
            for key, values in sorted(per_case_focus.items())
        },
        "errors": errors,
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary_view = {
        "model": report["model"],
        "architecture": report["architecture"],
        "cases": report["cases"],
        "repeats": report["repeats"],
        "evaluations": report["evaluations"],
        "scope": report["scope"],
        "routing": report["routing"],
        "focus": report["focus"],
        "model_latency_seconds": report["model_latency_seconds"],
        "end_to_end_latency_seconds": report["end_to_end_latency_seconds"],
        "errors": report["errors"],
    }
    print(json.dumps(summary_view, indent=2))
    print("WROTE:", args.output)

    passed = (
        errors == 0
        and scope_accuracy == 1.0
        and routing_accuracy == 1.0
        and all(value == 1.0 for value in class_recall.values())
        and sum(item["model_invoked"] for item in results) == expected_model_invocations
        and focus_accuracy >= args.min_focus_accuracy
    )
    if not passed:
        print("INTENT EVAL: FAIL — production scope/routing or advisory focus threshold was not met.",
              file=sys.stderr)
        return 2

    print("INTENT EVAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
