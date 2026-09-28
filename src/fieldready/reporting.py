"""Export a local supervisor review package without copying the raw source CSV."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from fieldready.storage import Store

_REPORT_FILES = ("summary.md", "findings.csv", "review_history.csv", "manifest.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _md(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _csv_safe(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.startswith(("=", "+", "@")):
        return "'" + value
    return value


def _csv_bytes(rows: list[dict], columns: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _csv_safe(row.get(column, "")) for column in columns})
    return stream.getvalue().encode("utf-8")


def _summary_markdown(summary: dict, findings: list[dict], history: list[dict]) -> bytes:
    severity = summary.get("severity_counts", {})
    rules = summary.get("rule_counts", {})
    categories = summary.get("category_counts", {})
    checks = summary.get("check_evaluations", {})
    reviews = summary["review_counts"]

    lines = [
        "# FieldReady Local — Supervisor Review Summary",
        "",
        f"- **Run ID:** {_md(summary['run_id'])}",
        f"- **Batch ID:** {_md(summary['batch_id'])}",
        f"- **Ruleset:** {_md(summary.get('ruleset', 'unknown'))}",
        f"- **Ruleset version:** {_md(summary.get('ruleset_version', 'unknown'))}",
        f"- **Ruleset title:** {_md(summary.get('ruleset_title', ''))}",
        f"- **Records:** {summary.get('row_count', 0)}",
        f"- **Findings:** {summary.get('finding_count', 0)}",
        f"- **Affected records:** {summary.get('affected_rows', 0)}",
        f"- **Unresolved findings:** {summary.get('unresolved_findings', 0)}",
        f"- **Rule evaluations:** {checks.get('evaluable', summary.get('total_checks_evaluable', 0))} evaluable; "
        f"{checks.get('not_evaluable', len(summary.get('total_checks_not_evaluable', [])))} not evaluable",
        "",
        "## Findings by severity",
        "",
        "| Severity | Count |",
        "| --- | ---: |",
    ]
    for key in ("critical", "high", "medium", "low"):
        if key in severity:
            lines.append(f"| {_md(key)} | {severity[key]} |")
    if not severity:
        lines.append("| — | 0 |")

    lines += [
        "",
        "## Current review status",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for key in ("open", "follow_up", "confirmed", "dismissed"):
        lines.append(f"| {_md(key)} | {reviews.get(key, 0)} |")

    lines += [
        "",
        "## Findings by rule",
        "",
        "| Rule | Count |",
        "| --- | ---: |",
    ]
    for key, value in sorted(rules.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {_md(key)} | {value} |")
    if not rules:
        lines.append("| — | 0 |")

    if categories:
        lines += [
            "",
            "## Findings by category",
            "",
            "| Category | Count |",
            "| --- | ---: |",
        ]
        for key, value in sorted(categories.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {_md(key)} | {value} |")

    lines += [
        "",
        "## Review queue snapshot",
        "",
        "| Record | Rule | Severity | Field | Observed | Expected | Status |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in findings:
        lines.append(
            f"| {item.get('row_number', '')} | {_md(item.get('rule_id', ''))} | "
            f"{_md(item.get('severity', ''))} | {_md(item.get('field', ''))} | "
            f"{_md(item.get('observed', '')) or '—'} | {_md(item.get('expected', '')) or '—'} | "
            f"{_md(item.get('status', ''))} |"
        )
    if not findings:
        lines.append("| — | — | — | — | — | — | — |")

    lines += [
        "",
        "## Audit trail",
        "",
        f"Recorded review events: **{len(history)}**.",
        "",
        "This package contains validation findings and review history only. "
        "**The raw source CSV is not included.**",
        "",
        "Generated locally by FieldReady Local. No cloud service is required.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def export_review_package(store: Store, run_id: str, output_dir: str | Path,
                          *, overwrite: bool = False) -> dict:
    summary = store.summary(run_id)
    findings = store.all_findings(run_id)
    history = store.review_history(run_id)
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    existing = [name for name in _REPORT_FILES if (destination / name).exists()]
    if existing and not overwrite:
        raise ValueError("Review package files already exist; use explicit overwrite to replace them.")

    finding_columns = [
        "finding_id", "row_number", "record_id", "rule_id", "category", "severity",
        "field", "observed", "expected", "status", "revision", "message", "verification",
    ]
    history_columns = [
        "event_id", "finding_id", "row_number", "record_id", "rule_id", "previous_status",
        "new_status", "revision", "reason", "created_at", "request_id",
    ]

    payloads = {
        "summary.md": _summary_markdown(summary, findings, history),
        "findings.csv": _csv_bytes(findings, finding_columns),
        "review_history.csv": _csv_bytes(history, history_columns),
    }
    manifest = {
        "format": "fieldready-review-package-v1",
        "generated_utc": _now(),
        "run_id": summary["run_id"],
        "batch_id": summary["batch_id"],
        "ruleset": summary.get("ruleset"),
        "ruleset_version": summary.get("ruleset_version"),
        "source_csv_included": False,
        "finding_count": summary.get("finding_count", 0),
        "review_event_count": len(history),
        "files": {name: {"sha256": _sha256(data), "bytes": len(data)}
                  for name, data in sorted(payloads.items())},
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode("utf-8")

    for name, data in payloads.items():
        temporary = destination / (name + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(destination / name)

    return {
        "output_dir": str(destination),
        "run_id": summary["run_id"],
        "ruleset": summary.get("ruleset"),
        "files": list(_REPORT_FILES),
        "source_csv_included": False,
    }
