"""Exercise the actual request guard; these are not MCP protocol tests."""
import unittest
from fieldready.security import LocalGuard

TOKEN = "synthetic_test_token_not_a_secret_123456"


class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, changes=None, extras=None):
        headers = {b"host": b"127.0.0.1:8000", b"authorization": b"Bearer " + TOKEN.encode()}
        for key, value in (changes or {}).items():
            if value is None:
                headers.pop(key, None)
            else:
                headers[key] = value
        messages = []
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
        async def send(message):
            messages.append(message)
        await LocalGuard(app, TOKEN, 8000)(
            {"type": "http", "headers": list(headers.items()) + (extras or [])}, None, send)
        return messages[0]["status"]

    async def test_valid_local_request(self):
        self.assertEqual(await self.request(), 200)

    async def test_missing_token_rejected(self):
        self.assertEqual(await self.request({b"authorization": None}), 401)

    async def test_wrong_token_rejected(self):
        self.assertEqual(await self.request({b"authorization": b"Bearer wrong"}), 401)

    async def test_rebinding_host_rejected(self):
        self.assertEqual(await self.request({b"host": b"attacker.example:8000"}), 421)

    async def test_external_origin_rejected(self):
        self.assertEqual(await self.request({b"origin": b"https://attacker.example"}), 403)

    async def test_null_origin_rejected(self):
        self.assertEqual(await self.request({b"origin": b"null"}), 403)

    async def test_explicit_local_origin_allowed(self):
        self.assertEqual(await self.request({b"origin": b"http://127.0.0.1:8501"}), 200)

    async def test_duplicate_security_headers_rejected(self):
        self.assertEqual(await self.request(extras=[(b"Host", b"127.0.0.1:8000")]), 400)

    async def test_weak_token_or_invalid_port_rejected(self):
        for token, port in (("short", 8000), (TOKEN, 0), (TOKEN, True), ("x" * 129, 8000)):
            with self.subTest(token=token, port=port):
                with self.assertRaises(ValueError):
                    LocalGuard(None, token, port)

    async def test_lifespan_forwarded(self):
        seen = []
        async def app(scope, receive, send):
            seen.append(scope["type"])
        await LocalGuard(app, TOKEN, 8000)({"type": "lifespan"}, None, None)
        self.assertEqual(seen, ["lifespan"])
