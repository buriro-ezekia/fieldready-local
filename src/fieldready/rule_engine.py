"""Versioned, package-owned survey rulesets for synthetic FieldReady demonstrations."""
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from importlib.resources import files
from typing import Any

from fieldready.rules import MAX_BYTES, MAX_ROWS, RULESET as LEGACY_RULESET

FIELD_RULESET = "field-survey-v1.0.0"
_RULESET_FILES = {FIELD_RULESET: "rulesets/field-survey-v1.0.0.json"}
_SUPPORTED_TYPES = {"string", "integer", "enum"}
_SUPPORTED_RULES = {"unique", "sum_equals", "less_equal", "between", "conditional_required"}


@dataclass(frozen=True)
class EngineFinding:
    row_number: int
    record_id: str
    rule_id: str
    field: str
    category: str
    severity: str
    observed: str
    expected: str
    message: str
    verification: str


def _legacy_metadata() -> dict[str, Any]:
    return {
        "id": LEGACY_RULESET,
        "version": "0.1",
        "title": "Synthetic household compatibility demo",
        "description": "Original four-column regression ruleset.",
        "record_id_field": "record_id",
        "demo_file": "data/survey.csv",
        "legacy": True,
    }


def list_rulesets() -> list[dict[str, Any]]:
    result = [_legacy_metadata()]
    for ruleset_id in sorted(_RULESET_FILES):
        spec = load_ruleset(ruleset_id)
        result.append({
            key: spec[key]
            for key in ("id", "version", "title", "description", "record_id_field", "demo_file")
        } | {"legacy": False})
    return result


def load_ruleset(ruleset_id: str) -> dict[str, Any]:
    if ruleset_id == LEGACY_RULESET:
        return _legacy_metadata()
    name = _RULESET_FILES.get(ruleset_id)
    if not name:
        raise ValueError("Unknown ruleset_id.")
    try:
        spec = json.loads(files("fieldready").joinpath(name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Packaged ruleset could not be loaded.") from exc
    _validate_spec(spec, ruleset_id)
    return spec


def _validate_spec(spec: object, expected_id: str) -> None:
    if not isinstance(spec, dict) or spec.get("id") != expected_id:
        raise ValueError("Packaged ruleset has an invalid identifier.")
    for key in ("version", "title", "description", "record_id_field", "demo_file"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError(f"Packaged ruleset is missing {key}.")
    columns = spec.get("columns")
    rules = spec.get("rules")
    if not isinstance(columns, dict) or not columns or spec["record_id_field"] not in columns:
        raise ValueError("Packaged ruleset columns are invalid.")
    if not isinstance(rules, list):
        raise ValueError("Packaged ruleset rules are invalid.")
    for field, cfg in columns.items():
        if not isinstance(field, str) or not isinstance(cfg, dict):
            raise ValueError("Packaged column definition is invalid.")
        if cfg.get("type") not in _SUPPORTED_TYPES:
            raise ValueError(f"Unsupported field type for {field}.")
        if cfg.get("type") == "enum":
            allowed = cfg.get("allowed")
            if not isinstance(allowed, list) or not allowed or not all(isinstance(v, str) for v in allowed):
                raise ValueError(f"Enum field {field} has invalid choices.")
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") not in _SUPPORTED_RULES:
            raise ValueError("Packaged rule definition is invalid.")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id or rule_id in seen:
            raise ValueError("Packaged rule IDs must be unique strings.")
        seen.add(rule_id)


def _decode_csv(data: bytes, columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise ValueError("Supply a UTF-8 CSV no larger than 1 MiB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding.") from exc
    if "\x00" in text:
        raise ValueError("CSV contains a null byte.")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = reader.fieldnames
        if headers is None or len(set(headers)) != len(headers) or set(headers) != set(columns):
            raise ValueError("Required columns, each once: " + ", ".join(columns))
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("A CSV record has the wrong number of fields.")
            rows.append({key: value.strip() for key, value in row.items()})
            if len(rows) > MAX_ROWS:
                raise ValueError("The prototype accepts at most 2,000 records.")
    except csv.Error as exc:
        raise ValueError("CSV parsing failed.") from exc
    if not rows:
        raise ValueError("CSV contains no records.")
    return rows


def read_for_ruleset(data: bytes, ruleset_id: str) -> list[dict[str, str]]:
    if ruleset_id == LEGACY_RULESET:
        from fieldready.rules import read_csv
        return read_csv(data)
    spec = load_ruleset(ruleset_id)
    return _decode_csv(data, tuple(spec["columns"]))


def demo_bytes(ruleset_id: str) -> bytes:
    spec = load_ruleset(ruleset_id)
    return files("fieldready").joinpath(spec["demo_file"]).read_bytes()


def _finding(row_number: int, record_id: str, rule_id: str, field: str, *,
             category: str, severity: str, observed: object, expected: object,
             message: str, verification: str) -> EngineFinding:
    return EngineFinding(
        row_number=row_number,
        record_id=record_id,
        rule_id=rule_id,
        field=field,
        category=category,
        severity=severity,
        observed="" if observed is None else str(observed),
        expected=str(expected),
        message=message,
        verification=verification,
    )


def _legacy_enriched(data: bytes) -> dict[str, Any]:
    from fieldready.rules import validate

    result = validate(data)
    categories = {
        "missing_id": ("completeness", "Record identifier is missing."),
        "duplicate_id": ("uniqueness", "Record identifier occurs more than once."),
        "missing_count": ("completeness", "Required count is missing."),
        "invalid_count": ("validity", "Count is outside the accepted integer domain."),
        "component_total": ("consistency", "Household total does not equal adults plus children."),
    }
    enriched = []
    for item in result["findings"]:
        category, message = categories[item["rule_id"]]
        enriched.append(item | {
            "category": category,
            "message": message,
            "verification": f"Check the source value for {item['field']} before recording a review outcome.",
        })
    severity_counts = Counter(item["severity"] for item in enriched)
    rule_counts = Counter(item["rule_id"] for item in enriched)
    result["findings"] = enriched
    result["ruleset_version"] = "0.1"
    result["ruleset_title"] = "Synthetic household compatibility demo"
    result["severity_counts"] = dict(sorted(severity_counts.items()))
    result["rule_counts"] = dict(sorted(rule_counts.items()))
    result["category_counts"] = dict(sorted(Counter(item["category"] for item in enriched).items()))
    result["check_evaluations"] = {
        "evaluable": result["total_checks_evaluable"],
        "not_evaluable": len(result["total_checks_not_evaluable"]),
    }
    return result


def validate_for_ruleset(data: bytes, ruleset_id: str) -> dict[str, Any]:
    if ruleset_id == LEGACY_RULESET:
        return _legacy_enriched(data)
    spec = load_ruleset(ruleset_id)
    rows = _decode_csv(data, tuple(spec["columns"]))
    record_field = spec["record_id_field"]
    findings: list[EngineFinding] = []
    parsed_rows: list[dict[str, int]] = []
    invalid_fields: list[set[str]] = []

    def add(row_number: int, row: dict[str, str], rule_id: str, field: str, *,
            category: str, severity: str, observed: object, expected: object,
            message: str, verification: str | None = None) -> None:
        findings.append(_finding(
            row_number, row.get(record_field, ""), rule_id, field,
            category=category, severity=severity, observed=observed, expected=expected,
            message=message,
            verification=verification or f"Check the source value for {field} before recording a review outcome.",
        ))

    for ordinal, row in enumerate(rows, start=1):
        parsed: dict[str, int] = {}
        invalid: set[str] = set()
        for field, cfg in spec["columns"].items():
            value = row[field]
            severity = cfg.get("severity", "high")
            if cfg.get("required") and not value:
                invalid.add(field)
                add(ordinal, row, f"{field}.required", field,
                    category="completeness", severity=severity, observed="",
                    expected="A non-empty value", message=f"{field} is required but missing.")
                continue
            if not value:
                continue
            if cfg["type"] == "integer":
                if not re.fullmatch(r"[+-]?[0-9]+", value):
                    invalid.add(field)
                    add(ordinal, row, f"{field}.integer", field,
                        category="validity", severity=severity, observed=value,
                        expected="An integer", message=f"{field} must be an integer.")
                    continue
                number = int(value)
                parsed[field] = number
                minimum = cfg.get("minimum")
                maximum = cfg.get("maximum")
                if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
                    invalid.add(field)
                    if minimum is not None and maximum is not None:
                        expected = f"An integer from {minimum} to {maximum}"
                    elif minimum is not None:
                        expected = f"An integer >= {minimum}"
                    else:
                        expected = f"An integer <= {maximum}"
                    add(ordinal, row, f"{field}.range", field,
                        category="validity", severity=severity, observed=value,
                        expected=expected, message=f"{field} is outside the permitted range.")
            elif cfg["type"] == "enum" and value not in cfg["allowed"]:
                invalid.add(field)
                add(ordinal, row, f"{field}.choice", field,
                    category="validity", severity=severity, observed=value,
                    expected="One of: " + ", ".join(cfg["allowed"]),
                    message=f"{field} contains an unsupported category.")
        parsed_rows.append(parsed)
        invalid_fields.append(invalid)

    not_evaluable: list[dict[str, Any]] = []
    evaluable = 0

    for rule in spec["rules"]:
        rule_type = rule["type"]
        rule_id = rule["id"]
        severity = rule.get("severity", "high")
        category = rule.get("category", "consistency")

        if rule_type == "unique":
            field = rule["field"]
            counts = Counter(
                row[field] for index, row in enumerate(rows)
                if row[field] and field not in invalid_fields[index]
            )
            for ordinal, row in enumerate(rows, start=1):
                value = row[field]
                if not value or field in invalid_fields[ordinal - 1]:
                    not_evaluable.append({"row_number": ordinal, "rule_id": rule_id})
                    continue
                evaluable += 1
                if counts[value] > 1:
                    add(ordinal, row, rule_id, field, category=category, severity=severity,
                        observed=value, expected="A unique identifier",
                        message=f"{field} occurs more than once in this batch.",
                        verification=f"Check every occurrence of {value} before recording a review outcome.")
            continue

        for ordinal, row in enumerate(rows, start=1):
            parsed = parsed_rows[ordinal - 1]
            invalid = invalid_fields[ordinal - 1]

            if rule_type == "sum_equals":
                target = rule["target"]
                components = rule["components"]
                needed = [target, *components]
                if any(field not in parsed or field in invalid for field in needed):
                    not_evaluable.append({"row_number": ordinal, "rule_id": rule_id})
                    continue
                evaluable += 1
                expected_number = sum(parsed[field] for field in components)
                if parsed[target] != expected_number:
                    add(ordinal, row, rule_id, target, category=category, severity=severity,
                        observed=row[target], expected=expected_number,
                        message=f"{target} does not equal " + " + ".join(components) + ".",
                        verification="Check the source component values and the reported total before deciding.")

            elif rule_type == "less_equal":
                left, right = rule["left"], rule["right"]
                if any(field not in parsed or field in invalid for field in (left, right)):
                    not_evaluable.append({"row_number": ordinal, "rule_id": rule_id})
                    continue
                evaluable += 1
                if parsed[left] > parsed[right]:
                    add(ordinal, row, rule_id, left, category=category, severity=severity,
                        observed=row[left], expected=f"<= {row[right]}",
                        message=f"{left} cannot exceed {right}.",
                        verification=f"Check the source values for {left} and {right} before deciding.")

            elif rule_type == "between":
                field = rule["field"]
                if field not in parsed or field in invalid:
                    not_evaluable.append({"row_number": ordinal, "rule_id": rule_id})
                    continue
                evaluable += 1
                value = parsed[field]
                if value < rule["minimum"] or value > rule["maximum"]:
                    add(ordinal, row, rule_id, field, category=category, severity=severity,
                        observed=row[field], expected=f"{rule['minimum']} to {rule['maximum']}",
                        message=rule["message"],
                        verification=rule.get("verification"))

            elif rule_type == "conditional_required":
                condition = rule["if"]
                condition_field = condition["field"]
                target = rule["field"]
                if condition_field in invalid:
                    not_evaluable.append({"row_number": ordinal, "rule_id": rule_id})
                    continue
                if row[condition_field] != condition["equals"]:
                    continue
                evaluable += 1
                if not row[target]:
                    add(ordinal, row, rule_id, target, category=category, severity=severity,
                        observed="", expected=rule["expected"], message=rule["message"],
                        verification=rule.get("verification"))

    findings.sort(key=lambda item: item.row_number)
    finding_dicts = [asdict(item) for item in findings]
    severity_counts = Counter(item.severity for item in findings)
    rule_counts = Counter(item.rule_id for item in findings)
    category_counts = Counter(item.category for item in findings)
    not_eval_rows = sorted({item["row_number"] for item in not_evaluable})

    return {
        "ruleset": spec["id"],
        "ruleset_version": spec["version"],
        "ruleset_title": spec["title"],
        "row_count": len(rows),
        "finding_count": len(findings),
        "affected_rows": len({item.row_number for item in findings}),
        "severity_counts": dict(sorted(severity_counts.items())),
        "rule_counts": dict(sorted(rule_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "check_evaluations": {"evaluable": evaluable, "not_evaluable": len(not_evaluable)},
        "rules_not_evaluable": not_evaluable,
        "total_checks_evaluable": evaluable,
        "total_checks_not_evaluable": not_eval_rows,
        "findings": finding_dicts,
    }
