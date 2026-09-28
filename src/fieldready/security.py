"""Small ASGI guard for a loopback-only, single-user prototype, not public OAuth."""
import hmac
import re


class LocalGuard:
    def __init__(self, app, token: str, port: int):
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
            raise ValueError("Set FIELDREADY_MCP_TOKEN to 32–128 random URL-safe characters.")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("port must be an integer from 1 to 65535.")
        self.app = app
        self.auth = b"Bearer " + token.encode("ascii")
        self.hosts = {f"127.0.0.1:{port}".encode(), f"localhost:{port}".encode()}
        self.origins = {b"http://127.0.0.1:8501", b"http://localhost:8501"}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {}
        duplicates = False
        for name, value in scope.get("headers", []):
            name = name.lower()
            if name in (b"host", b"origin", b"authorization") and name in headers:
                duplicates = True
            headers[name] = value
        status = 0
        if duplicates:
            status = 400
        elif headers.get(b"host") not in self.hosts:
            status = 421
        elif b"origin" in headers and headers[b"origin"] not in self.origins:
            status = 403
        elif not hmac.compare_digest(headers.get(b"authorization", b""), self.auth):
            status = 401
        if status:
            await send({"type": "http.response.start", "status": status,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"cache-control", b"no-store")]})
            await send({"type": "http.response.body", "body": b'{"error":"Request rejected"}'})
            return
        return await self.app(scope, receive, send)
