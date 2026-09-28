"""Official MCP SDK v2 adapter; full HTTP execution must pass check_mcp.py."""
import argparse
import os
from pathlib import Path
from typing import Any

from fieldready.cli import default_db
from fieldready.security import LocalGuard
from fieldready.storage import Store


def build_app(db_path: Path, token: str, port: int):
    from mcp.server import MCPServer

    store = Store(db_path)
    server = MCPServer("FieldReady Local", version="0.1.0")

    @server.tool(structured_output=True)
    def validate_batch(batch_id: str, request_id: str) -> dict[str, Any]:
        """Validate an already imported batch; return counts, not all respondent rows."""
        run = store.validate_batch(batch_id, request_id)
        return store.summary(run["run_id"])

    @server.tool(structured_output=True)
    def list_findings(run_id: str, status: str | None = None,
                      limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """Read a bounded findings page; never infer whole-batch counts from a page."""
        return store.list_findings(run_id, status=status, limit=limit, offset=offset)

    @server.tool(structured_output=True)
    def get_review_summary(run_id: str) -> dict[str, Any]:
        """Read authoritative counts and current persisted review state."""
        return store.summary(run_id)

    # No review-write, arbitrary path, shell, SQL, or network-fetch tools are exposed.
    app = server.streamable_http_app(host="127.0.0.1", stateless_http=True,
                                     json_response=True, max_request_body_size=65_536)
    return LocalGuard(app, token, port)


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=default_db())
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    token = os.environ.get("FIELDREADY_MCP_TOKEN", "")
    # Validate the local credential before opening a database or network listener.
    LocalGuard(None, token, args.port)
    app = build_app(args.db, token, args.port)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
