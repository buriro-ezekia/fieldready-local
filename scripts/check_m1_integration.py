"""Real M1 HTTP -> MCP -> web -> SQLite -> export -> restart integration check.

Does not render a browser and does not run local-model inference.
"""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import secrets
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_export(output: Path, run_id: str) -> dict:
    expected_names = {"summary.md", "findings.csv", "review_history.csv", "manifest.json"}
    require(output.is_dir(), "M1 export directory was not created.")
    require({path.name for path in output.iterdir()} == expected_names,
            "M1 export package file set is incorrect.")

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["format"] == "fieldready-review-package-v1",
            "M1 export manifest format is incorrect.")
    require(manifest["run_id"] == run_id, "M1 export manifest run_id changed.")
    require(manifest["ruleset"] == "field-survey-v1.0.0",
            "M1 export manifest ruleset is incorrect.")
    require(manifest["finding_count"] == 17, "M1 export manifest finding count is incorrect.")
    require(manifest["review_event_count"] == 1, "M1 export manifest review count is incorrect.")
    require(manifest["source_csv_included"] is False, "M1 export unexpectedly included raw source CSV.")

    for name, metadata in manifest["files"].items():
        payload = (output / name).read_bytes()
        require(hashlib.sha256(payload).hexdigest() == metadata["sha256"],
                f"M1 export hash mismatch for {name}.")
        require(len(payload) == metadata["bytes"], f"M1 export byte count mismatch for {name}.")

    return manifest


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    missing = [
        name for name in ("mcp", "httpx2", "uvicorn")
        if importlib.util.find_spec(name) is None
    ]
    if missing:
        print("M1 INTEGRATION: NOT RUN — missing " + ", ".join(missing), file=sys.stderr)
        return 2

    from check_mcp import serve
    from check_web import request, web_server
    from fieldready.mcp_client import MCPGateway
    from fieldready.rule_engine import FIELD_RULESET, demo_bytes
    from fieldready.storage import Store

    try:
        with tempfile.TemporaryDirectory(prefix="fieldready-m1-integration-") as folder:
            root = Path(folder)
            db = root / "review.sqlite3"
            store = Store(db)
            batch_id = store.register(demo_bytes(FIELD_RULESET), FIELD_RULESET)

            mcp_token = secrets.token_urlsafe(32)
            web_token = secrets.token_urlsafe(32)

            # Direct real MCP path.
            with serve(db, mcp_token) as url:
                mcp_port = int(url.split(":")[2].split("/")[0])
                gateway = MCPGateway(mcp_port, mcp_token)
                health = asyncio.run(gateway.ping())
                require(health["protocol"] >= "2025-11-25", "M1 MCP protocol is too old.")
                require(
                    set(health["tools"]) ==
                    {"validate_batch", "list_findings", "get_review_summary"},
                    "M1 changed the bounded MCP tool surface.",
                )

                summary = asyncio.run(gateway.call("validate_batch", {
                    "batch_id": batch_id,
                    "request_id": "m1-direct-http-validation",
                }))
                require(summary["ruleset"] == FIELD_RULESET, "M1 direct MCP ruleset changed.")
                require(
                    (summary["row_count"], summary["finding_count"], summary["affected_rows"])
                    == (14, 17, 13),
                    "M1 direct MCP headline counts are incorrect.",
                )
                require(
                    summary["severity_counts"] ==
                    {"critical": 3, "high": 9, "medium": 5},
                    "M1 direct MCP severity counts are incorrect.",
                )
                require(
                    summary["check_evaluations"] ==
                    {"evaluable": 80, "not_evaluable": 5},
                    "M1 direct MCP rule-evaluation counts are incorrect.",
                )

                page = asyncio.run(gateway.call("list_findings", {
                    "run_id": summary["run_id"],
                    "limit": 100,
                    "offset": 0,
                }))
                require(page["total_matching"] == 17 and len(page["items"]) == 17,
                        "M1 direct MCP findings page is incomplete.")
                rich = next(
                    (item for item in page["items"] if item["rule_id"] == "gps.accuracy"),
                    None,
                )
                require(rich is not None, "M1 GPS finding was not returned through MCP.")
                require(
                    all(key in rich for key in ("category", "severity", "message", "verification")),
                    "M1 rich finding metadata was lost through MCP.",
                )

                # Real web -> MCP path using the richer built-in demo.
                with web_server(db, gateway, web_token) as web_port:
                    status, info = request(web_port, web_token, "/api/info")
                    require(status == 200, "M1 web info failed.")
                    require(
                        FIELD_RULESET in {item["id"] for item in info["rulesets"]},
                        "M1 web ruleset catalogue is incomplete.",
                    )

                    status, initial = request(
                        web_port, web_token, "/api/demo-field",
                        {"request_id": "m1-web-demo"},
                    )
                    require(status == 200, "M1 web field-survey demo failed.")
                    require(
                        (initial["row_count"], initial["finding_count"], initial["affected_rows"])
                        == (14, 17, 13),
                        "M1 web/MCP headline counts are incorrect.",
                    )
                    run_id = initial["run_id"]

                    status, data = request(web_port, web_token, "/api/run", {"run_id": run_id})
                    require(status == 200, "M1 web evidence retrieval failed.")
                    require(data["summary"]["ruleset"] == FIELD_RULESET,
                            "M1 web summary lost the ruleset.")
                    require(len(data["page"]["items"]) == 17,
                            "M1 web findings page is incomplete.")

                    first = data["page"]["items"][0]
                    decision = {
                        "finding_id": first["finding_id"],
                        "status": "confirmed",
                        "reason": "M1 synthetic integration review",
                        "expected_revision": first["revision"],
                        "request_id": "m1-web-review",
                        "confirmed": False,
                    }
                    require(
                        request(web_port, web_token, "/api/decision", decision)[0] == 400,
                        "M1 accepted an unconfirmed review write.",
                    )
                    decision["confirmed"] = True
                    require(
                        request(web_port, web_token, "/api/decision", decision)[0] == 200,
                        "M1 confirmed review write failed.",
                    )

                    status, exported = request(
                        web_port, web_token, "/api/export", {"run_id": run_id}
                    )
                    require(status == 200, "M1 browser export action failed.")
                    require(exported["source_csv_included"] is False,
                            "M1 browser export reported source inclusion.")

                    export_dir = Path(exported["output_dir"])
                    expected_dir = db.parent / "exports" / run_id
                    require(export_dir.samefile(expected_dir),
                            "M1 browser export escaped the application-controlled directory.")
                    manifest = verify_export(export_dir, run_id)

            # Restart the real MCP and web services and verify persisted review/export state.
            with serve(db, mcp_token) as url:
                mcp_port = int(url.split(":")[2].split("/")[0])
                gateway = MCPGateway(mcp_port, mcp_token)
                with web_server(db, gateway, web_token) as web_port:
                    status, data = request(web_port, web_token, "/api/run", {"run_id": run_id})
                    require(status == 200, "M1 reviewed run did not reopen after restart.")
                    require(data["summary"]["unresolved_findings"] == 16,
                            "M1 confirmed review did not persist after restart.")
                    require(data["summary"]["review_counts"]["confirmed"] == 1,
                            "M1 review count changed after restart.")
                    require(data["summary"]["finding_count"] == 17,
                            "M1 finding count changed after restart.")

                    status, exported_again = request(
                        web_port, web_token, "/api/export", {"run_id": run_id}
                    )
                    require(status == 200, "M1 export failed after restart.")
                    require(Path(exported_again["output_dir"]).samefile(export_dir),
                            "M1 export directory changed after restart.")
                    manifest_after = verify_export(export_dir, run_id)
                    require(
                        manifest_after["finding_count"] == manifest["finding_count"] == 17,
                        "M1 export evidence changed after restart.",
                    )

            print("M1 MCP protocol:", health["protocol"])
            print(json.dumps({
                "ruleset": FIELD_RULESET,
                "rows": 14,
                "findings": 17,
                "affected_rows": 13,
                "severity_counts": {"critical": 3, "high": 9, "medium": 5},
                "check_evaluations": {"evaluable": 80, "not_evaluable": 5},
                "unresolved_after_one_confirmation": 16,
                "export_files": [
                    "summary.md", "findings.csv", "review_history.csv", "manifest.json"
                ],
                "source_csv_included": False,
                "mcp_tools": health["tools"],
            }, indent=2))

        print(
            "M1 REAL MCP + WEB + EXPORT + RESTART: PASS "
            "(browser rendering and local-model inference NOT tested)"
        )
        return 0

    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print("M1 INTEGRATION: FAIL — " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
