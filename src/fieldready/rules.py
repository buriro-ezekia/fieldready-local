"""Validate a deliberately fictional household questionnaire; never modify input."""

import csv
import io
import re
from collections import Counter
from dataclasses import asdict, dataclass

MAX_BYTES = 1_048_576
MAX_ROWS = 2_000
COLUMNS = ("record_id", "adults", "children", "household_size")
RULESET = "synthetic-household-v0.1"


@dataclass(frozen=True)
class Finding:
    row_number: int
    record_id: str
    rule_id: str
    field: str
    severity: str
    observed: str
    expected: str


def read_csv(data: bytes) -> list[dict[str, str]]:
    """Preserve string identifiers; row_number means record ordinal, not line number."""
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
        if headers is None or len(set(headers)) != len(headers) or set(headers) != set(COLUMNS):
            raise ValueError("Required columns, each once: " + ", ".join(COLUMNS))
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


def validate(data: bytes) -> dict:
    """Return deterministic findings and explicitly non-evaluable total checks."""
    rows = read_csv(data)
    identifiers = Counter(row["record_id"] for row in rows if row["record_id"])
    findings: list[Finding] = []
    not_evaluable: list[int] = []
    for ordinal, row in enumerate(rows, start=1):
        def add(rule: str, field: str, observed: str, expected: str) -> None:
            findings.append(Finding(ordinal, row["record_id"], rule, field,
                                    "high", observed, expected))

        if not row["record_id"]:
            add("missing_id", "record_id", "", "A non-empty identifier")
        elif identifiers[row["record_id"]] > 1:
            add("duplicate_id", "record_id", row["record_id"], "A unique identifier")
        numbers: dict[str, int] = {}
        for field in COLUMNS[1:]:
            value = row[field]
            if not value:
                add("missing_count", field, value, "An integer from 0 to 100")
            elif not re.fullmatch(r"[0-9]{1,3}", value) or int(value) > 100:
                add("invalid_count", field, value, "An integer from 0 to 100")
            else:
                numbers[field] = int(value)
        if len(numbers) != 3:
            not_evaluable.append(ordinal)
        elif numbers["adults"] + numbers["children"] != numbers["household_size"]:
            add("component_total", "household_size", str(numbers["household_size"]),
                str(numbers["adults"] + numbers["children"]))
    return {
        "ruleset": RULESET,
        "row_count": len(rows),
        "finding_count": len(findings),
        "affected_rows": len({item.row_number for item in findings}),
        "total_checks_evaluable": len(rows) - len(not_evaluable),
        "total_checks_not_evaluable": not_evaluable,
        "findings": [asdict(item) for item in findings],
    }
