"""Evaluate local intent classification accuracy and latency on synthetic questions."""
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
    parser.add_argument("--min-accuracy", type=float, default=0.90)
    parser.add_argument("--min-class-recall", type=float, default=0.85)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "intent-eval.json")
    args = parser.parse_args()

    if args.repeats < 1 or args.repeats > 10:
        parser.error("--repeats must be between 1 and 10.")
    if not 0 <= args.min_accuracy <= 1 or not 0 <= args.min_class_recall <= 1:
        parser.error("Thresholds must be between 0 and 1.")
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
    for case in cases:
        if case.get("expected") not in {"in_scope", "out_of_scope"} or not isinstance(case.get("question"), str):
            print("INTENT EVAL: FAIL — malformed case: " + repr(case), file=sys.stderr)
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
                        model_elapsed = float(result["elapsed_seconds"]) if result["model_invoked"] else None
                        routing_source = result["routing_source"]
                        model_invoked = bool(result["model_invoked"])
                        if predicted == "in_scope" and result["text"] != expected_grounded:
                            raise RuntimeError("In-scope response was not deterministic grounded output.")
                        if result["finding_id"] != finding["finding_id"]:
                            raise RuntimeError("Evidence reference changed during evaluation.")
                        error = None
                    except Exception as exc:
                        predicted, model_elapsed, routing_source, model_invoked = (
                            "error", None, "error", False
                        )
                        error = type(exc).__name__ + ": " + str(exc)
                    end_to_end = round(time.monotonic() - wall_started, 4)
                    expected_route = "local_model" if case["expected"] == "in_scope" else "deterministic_scope_guard"
                    results.append({
                        "id": case["id"],
                        "repeat": repeat,
                        "expected": case["expected"],
                        "predicted": predicted,
                        "correct": predicted == case["expected"],
                        "routing_source": routing_source,
                        "expected_routing_source": expected_route,
                        "routing_correct": routing_source == expected_route,
                        "model_invoked": model_invoked,
                        "model_elapsed_seconds": model_elapsed,
                        "end_to_end_elapsed_seconds": end_to_end,
                        "error": error,
                    })
                    label = "PASS" if results[-1]["correct"] and results[-1]["routing_correct"] else "MISS"
                    route = results[-1]["routing_source"]
                    print(f"{case['id']} repeat {repeat}: {case['expected']} -> {predicted} "
                          f"via {route} [{label}]")
    except (OSError, RuntimeError, ValueError) as exc:
        print("INTENT EVAL: FAIL — " + str(exc), file=sys.stderr)
        return 2

    total = len(results)
    correct = sum(item["correct"] for item in results)
    accuracy = correct / total
    recalls = {}
    for label in ("in_scope", "out_of_scope"):
        subset = [item for item in results if item["expected"] == label]
        recalls[label] = sum(item["correct"] for item in subset) / len(subset)

    model_latencies = [
        item["model_elapsed_seconds"] for item in results
        if item["model_elapsed_seconds"] is not None
    ]
    end_to_end_latencies = [item["end_to_end_elapsed_seconds"] for item in results]
    confusion = Counter((item["expected"], item["predicted"]) for item in results)
    case_accuracy = defaultdict(list)
    for item in results:
        case_accuracy[item["id"]].append(item["correct"])

    report = {
        "model": args.model,
        "cases": len(cases),
        "repeats": args.repeats,
        "evaluations": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "class_recall": {key: round(value, 4) for key, value in recalls.items()},
        "routing": {
            "correct": sum(item["routing_correct"] for item in results),
            "accuracy": round(sum(item["routing_correct"] for item in results) / total, 4),
            "model_invocations": sum(item["model_invoked"] for item in results),
            "guarded_requests": sum(item["routing_source"] == "deterministic_scope_guard" for item in results),
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
        "confusion": {
            f"{expected}->{predicted}": count
            for (expected, predicted), count in sorted(confusion.items())
        },
        "per_case_accuracy": {
            key: round(sum(values) / len(values), 4)
            for key, values in sorted(case_accuracy.items())
        },
        "thresholds": {
            "min_accuracy": args.min_accuracy,
            "min_class_recall": args.min_class_recall,
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "model", "cases", "repeats", "evaluations", "correct", "accuracy",
        "class_recall", "routing", "model_latency_seconds", "end_to_end_latency_seconds", "confusion"
    )}, indent=2))
    print("WROTE:", args.output)

    errors = sum(item["predicted"] == "error" for item in results)
    routing_accuracy = sum(item["routing_correct"] for item in results) / total
    passed = (
        errors == 0
        and accuracy >= args.min_accuracy
        and all(value >= args.min_class_recall for value in recalls.values())
        and routing_accuracy == 1.0
    )
    if not passed:
        print("INTENT EVAL: FAIL — thresholds were not met.", file=sys.stderr)
        return 2
    print("INTENT EVAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
