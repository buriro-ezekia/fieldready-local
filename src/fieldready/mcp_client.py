"""Browser-side MCP client. Never replace a failed connection with direct validation."""
import asyncio
import re

TOOLS = frozenset({"validate_batch", "list_findings", "get_review_summary"})


class MCPGateway:
    def __init__(self, port: int, token: str):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid local MCP port.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
            raise ValueError("Invalid local MCP credential.")
        self.url = f"http://127.0.0.1:{port}/mcp"
        self.token = token

    async def call(self, name: str, arguments: dict) -> dict:
        if name not in TOOLS:
            raise ValueError("Tool is not permitted.")
        try:
            return await asyncio.wait_for(self._call(name, arguments), timeout=30)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError("MCP request failed. Check the local server; no fallback was used.") from exc

    async def _call(self, name: str, arguments: dict) -> dict:
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client

        async with httpx2.AsyncClient(headers={"Authorization": "Bearer " + self.token},
                                      timeout=20, trust_env=False, follow_redirects=False) as http:
            async with Client(streamable_http_client(self.url, http_client=http)) as client:
                protocol = client.protocol_version
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", protocol) or protocol < "2025-11-25":
                    raise RuntimeError("Unsupported negotiated MCP protocol.")
                tools = await client.list_tools()
                if {tool.name for tool in tools.tools} != TOOLS:
                    raise RuntimeError("Unexpected MCP tool exposure.")
                result = await client.call_tool(name, arguments)
                if result.is_error:
                    raise ValueError("MCP rejected this request. Reload the run and check its identifiers.")
                if not isinstance(result.structured_content, dict):
                    raise RuntimeError("MCP did not return structured evidence.")
                return result.structured_content
