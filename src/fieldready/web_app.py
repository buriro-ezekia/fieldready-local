"""Local authenticated browser surface. Review writes remain separate from model access."""
import asyncio
import hmac
import json
import re
import sqlite3
from pathlib import Path

from fieldready.rule_engine import FIELD_RULESET, LEGACY_RULESET, demo_bytes, list_rulesets
from fieldready.rules import MAX_BYTES
from fieldready.storage import Store

ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8")}
MAX_BODY = 2_097_152


def fields(body: dict, required: set, optional: set = frozenset()) -> None:
    if not required <= body.keys() or body.keys() - required - optional:
        raise ValueError("Request fields do not match this action.")


class WebApp:
    def __init__(self, db_path, gateway, token: str, port: int, explainer=None):
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
            raise ValueError("Invalid web credential.")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid web port.")
        self.db_path = Path(db_path).resolve()
        self.store = Store(self.db_path)
        self.gateway = gateway
        self.explainer = explainer
        self.auth = ("Bearer " + token).encode()
        self.host = f"127.0.0.1:{port}".encode()
        self.origin = b"http://" + self.host
        self.model_lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif event["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":
            return

        headers = {}
        for key, value in scope.get("headers", []):
            key = key.lower()
            if key in headers and key in (b"host", b"origin", b"authorization", b"content-length"):
                return await self.reply(send, 400, {"error": "Duplicate security header."})
            headers[key] = value
        if headers.get(b"host") != self.host:
            return await self.reply(send, 421, {"error": "Use the printed 127.0.0.1 address."})
        if b"origin" in headers and headers[b"origin"] != self.origin:
            return await self.reply(send, 403, {"error": "Foreign origin rejected."})

        path, method = scope["path"], scope["method"]
        if path in ASSETS and method == "GET":
            from importlib.resources import files
            name, content_type = ASSETS[path]
            data = files("fieldready").joinpath("web_assets/" + name).read_bytes()
            return await self.reply(send, 200, data, content_type)

        if not hmac.compare_digest(headers.get(b"authorization", b""), self.auth):
            return await self.reply(send, 401, {"error": "Open the full session link printed by the launcher."})

        try:
            if path == "/api/info" and method == "GET":
                mcp_health = await self.gateway.ping()
                with self.store.connection() as db:
                    runs = [dict(row) for row in db.execute(
                        """SELECT r.id,r.created_at,b.ruleset_id
                           FROM runs r JOIN batches b ON b.id=r.batch_id
                           ORDER BY r.created_at DESC LIMIT 100"""
                    )]
                result = {
                    "runs": runs,
                    "rulesets": list_rulesets(),
                    "model": self.explainer.model if self.explainer else None,
                    "mcp": mcp_health,
                    "notice": "Synthetic data only. No live Alexa+ integration.",
                }

            elif path.startswith("/api/") and method == "POST":
                if headers.get(b"content-type", b"").split(b";")[0] != b"application/json":
                    return await self.reply(send, 415, {"error": "JSON content type required."})
                raw = bytearray()
                while True:
                    event = await asyncio.wait_for(receive(), timeout=10)
                    if event["type"] == "http.disconnect":
                        return
                    raw.extend(event.get("body", b""))
                    if len(raw) > MAX_BODY:
                        return await self.reply(send, 413, {"error": "Request too large."})
                    if not event.get("more_body"):
                        break
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError("Request must be a JSON object.")
                result = await self.action(path, body)

            else:
                return await self.reply(send, 404, {"error": "No such route or method."})

            await self.reply(send, 200, result)

        except (ValueError, TypeError, KeyError) as exc:
            await self.reply(send, 400, {"error": str(exc)})
        except (RuntimeError, OSError, sqlite3.Error, TimeoutError):
            await self.reply(
                send, 503,
                {"error": "Local service unavailable. Check the terminal, model name and installation. No fallback was used."},
            )

    async def action(self, path: str, body: dict) -> dict:
        if path in ("/api/demo", "/api/demo-field", "/api/import"):
            optional = {"ruleset_id"} if path == "/api/import" else set()
            required = {"request_id"} | ({"csv"} if path == "/api/import" else set())
            fields(body, required, optional)

            if path == "/api/demo":
                ruleset_id = LEGACY_RULESET
                data = demo_bytes(ruleset_id)
            elif path == "/api/demo-field":
                ruleset_id = FIELD_RULESET
                data = demo_bytes(ruleset_id)
            else:
                if not isinstance(body["csv"], str):
                    raise ValueError("CSV content must be text.")
                data = body["csv"].encode("utf-8")
                ruleset_id = body.get("ruleset_id", LEGACY_RULESET)

            if len(data) > MAX_BYTES:
                raise ValueError("CSV exceeds 1 MiB.")
            batch = await asyncio.to_thread(self.store.register, data, ruleset_id)
            return await self.gateway.call(
                "validate_batch", {"batch_id": batch, "request_id": body["request_id"]}
            )

        if path == "/api/run":
            fields(body, {"run_id"}, {"status", "offset"})
            summary = await self.gateway.call("get_review_summary", {"run_id": body["run_id"]})
            page = await self.gateway.call("list_findings", {
                "run_id": body["run_id"],
                "status": body.get("status"),
                "offset": body.get("offset", 0),
                "limit": 50,
            })
            return {"summary": summary, "page": page}

        if path == "/api/decision":
            fields(body, {"finding_id", "status", "reason", "expected_revision", "request_id", "confirmed"})
            return await asyncio.to_thread(self.store.decide, **body)

        if path == "/api/export":
            fields(body, {"run_id"})
            from fieldready.reporting import export_review_package
            output_dir = self.db_path.parent / "exports" / body["run_id"]
            return await asyncio.to_thread(
                export_review_package, self.store, body["run_id"], output_dir, overwrite=True
            )

        if path == "/api/explain":
            fields(body, {"run_id", "finding_id", "question"})
            if self.explainer is None:
                raise ValueError("AI is disabled. Restart the launcher with --model and an installed local model.")
            if self.model_lock.locked():
                raise ValueError("An explanation is already running. Review its result before sending another.")
            if not isinstance(body["finding_id"], str) or not re.fullmatch(r"[a-f0-9]{32}:[0-9]{1,5}", body["finding_id"]):
                raise ValueError("Invalid finding identifier.")
            run, ordinal = body["finding_id"].split(":")
            if run != body["run_id"] or not 1 <= int(ordinal) <= 10000:
                raise ValueError("Finding does not belong to the selected run.")
            async with self.model_lock:
                summary = await self.gateway.call("get_review_summary", {"run_id": run})
                page = await self.gateway.call("list_findings", {
                    "run_id": run, "offset": int(ordinal) - 1, "limit": 1,
                })
                if not page["items"] or page["items"][0]["finding_id"] != body["finding_id"]:
                    raise ValueError("Finding was not found.")
                return await asyncio.to_thread(
                    self.explainer.explain, summary, page["items"][0], body["question"]
                )

        raise ValueError("Unknown action.")

    @staticmethod
    async def reply(send, status, value, content_type="application/json; charset=utf-8"):
        data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=True).encode()
        headers = [
            (b"content-type", content_type.encode()),
            (b"content-length", str(len(data)).encode()),
            (b"cache-control", b"no-store"),
            (b"x-content-type-options", b"nosniff"),
            (b"referrer-policy", b"no-referrer"),
            (b"x-frame-options", b"DENY"),
            (b"content-security-policy",
             b"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
             b"base-uri 'none'; form-action 'self'; frame-ancestors 'none'"),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": data})
