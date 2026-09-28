"""Deterministic scope router, local review-focus classifier and evidence renderer.

Scope is decided deterministically. Clearly unrelated requests are rejected without
inference. In-scope review questions reach the local model only for a non-critical focus
classification. Python renders all factual content from verified evidence.
"""
import http.client
import json
import re
import time

FOCUS_SYSTEM = (
    "Classify the review focus of one in-scope supervisor question about a selected "
    "survey-validation finding. Return exactly one focus: reason, verification, evidence, "
    "review_guidance, or combined. reason = asks why/why flagged; verification = asks what "
    "to check/verify/compare; evidence = asks what observed/expected/displayed evidence means; "
    "review_guidance = asks how to review/decide; combined = explicitly asks both why and what "
    "to verify. Examples: 'Why was this finding raised?' -> reason; 'What should I verify?' -> "
    "verification; 'What do observed and expected mean?' -> evidence; 'How should I review this "
    "before deciding?' -> review_guidance; 'Why was this flagged and what should I verify?' -> "
    "combined. Do not answer the question. Return JSON only."
)

FOCUS_FORMAT = {
    "type": "object",
    "properties": {
        "focus": {
            "type": "string",
            "enum": ["reason", "verification", "evidence", "review_guidance", "combined"],
        },
    },
    "required": ["focus"],
    "additionalProperties": False,
}

SUPPORTED_FOCUS = frozenset({"reason", "verification", "evidence", "review_guidance", "combined"})

_SCOPE_STRONG = re.compile(
    r"\b(finding|evidence|verify|validation|record|rule|observed|expected|status|flagged|"
    r"component_total|duplicate_id|missing_id|missing_count|invalid_count|household_size)\b",
    re.IGNORECASE,
)
_SCOPE_WEAK = frozenset({
    "review", "check", "compare", "source", "outcome", "decision", "confirm", "dismiss",
    "followup", "follow-up", "value",
})
_SCOPE_OVERRIDE = re.compile(
    r"\b(ignore|disregard|forget|bypass)\b.{0,80}\b(review|task|instruction|finding|evidence)\b"
    r"|\b(tell|give)\s+me\b.{0,40}\b(joke|poem|recipe)\b",
    re.IGNORECASE,
)
_GENERIC_REVIEW = re.compile(
    r"^\s*(why\??|what\s+should\s+i\s+(check|verify)\??|what\s+does\s+this\s+mean\??|"
    r"how\s+should\s+i\s+(review|handle)\s+this\??)\s*$",
    re.IGNORECASE,
)


def safe_model_name(name: str) -> str:
    if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", name)
            or "cloud" in name.lower() or "://" in name):
        raise ValueError("Specify an installed local model, not a cloud model or URL.")
    return name


def scope_guard(question: str) -> str:
    """Return the final deterministic scope decision."""
    text = question.strip()
    if _SCOPE_OVERRIDE.search(text):
        return "out_of_scope"
    if _GENERIC_REVIEW.fullmatch(text):
        return "in_scope"
    if _SCOPE_STRONG.search(text):
        return "in_scope"
    tokens = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z_-]*", text)}
    if len(tokens & _SCOPE_WEAK) >= 2:
        return "in_scope"
    return "out_of_scope"


def _display(value: object) -> str:
    return "(missing)" if value is None or value == "" else str(value)


def grounded_text(finding: dict) -> str:
    row = finding["row_number"]
    rule = finding["rule_id"]
    field = finding["field"]
    observed = _display(finding["observed"])
    expected = _display(finding["expected"])
    explanations = {
        "component_total": (
            f"Rule component_total · record ordinal {row}. "
            f"The finding was raised because {field} is recorded as {observed}, "
            f"while the validated component total is {expected}. "
            f"Verification: check the source component values and {field} before recording a review outcome."
        ),
        "duplicate_id": (
            f"Rule duplicate_id · record ordinal {row}. "
            f"The finding was raised because the record_id value {observed} occurs more than once in this batch; "
            f"the rule expects {expected}. "
            "Verification: check the other occurrence or occurrences of that identifier before recording a review outcome."
        ),
        "missing_id": (
            f"Rule missing_id · record ordinal {row}. "
            f"The finding was raised because record_id is {observed}; the rule expects {expected}. "
            "Verification: check the source record for the required identifier before recording a review outcome."
        ),
        "missing_count": (
            f"Rule missing_count · record ordinal {row}. "
            f"The finding was raised because {field} is {observed}; the rule expects {expected}. "
            f"Verification: check the source value for {field} before recording a review outcome."
        ),
        "invalid_count": (
            f"Rule invalid_count · record ordinal {row}. "
            f"The finding was raised because {field} is recorded as {observed}; the rule expects {expected}. "
            f"Verification: check the source value for {field} before recording a review outcome."
        ),
    }
    if rule in explanations:
        return explanations[rule]

    message = finding.get("message")
    verification = finding.get("verification")
    if isinstance(message, str) and message.strip():
        verify_text = (
            verification.strip()
            if isinstance(verification, str) and verification.strip()
            else f"Check the displayed evidence for {field} against the source before deciding."
        )
        return (
            f"Rule {rule} · record ordinal {row}. {message.strip()} "
            f"Observed: {observed}; expected: {expected}. Verification: {verify_text}"
        )

    return (
        f"Rule {rule} · record ordinal {row}. The finding concerns {field}: observed {observed}; "
        f"expected {expected}. Verification: check the displayed evidence against the source before "
        "recording a review outcome."
    )


def _decline_text(finding: dict) -> str:
    return (
        f"Rule {finding['rule_id']} · record ordinal {finding['row_number']}. "
        "That question is outside this finding-review assistant's scope. "
        "Ask why this finding was raised or what evidence should be verified before a review decision."
    )


class LocalExplainer:
    def __init__(self, model: str, port: int = 11435):
        self.model = safe_model_name(model)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid local Ollama port.")
        self.port = port

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        try:
            encoded = json.dumps(body).encode() if body is not None else None
            connection.request(method, path, body=encoded, headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            data = response.read(262_145)
            if response.status != 200 or len(data) > 262_144:
                raise RuntimeError("Local model request failed or exceeded the response limit.")
            value = json.loads(data)
            if not isinstance(value, dict) or value.get("error"):
                raise RuntimeError("Local model returned an invalid response.")
            return value
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise RuntimeError("Local Ollama is unavailable or returned invalid JSON; no cloud fallback.") from exc
        finally:
            connection.close()

    @staticmethod
    def _validate_focus(payload: object) -> str:
        if not isinstance(payload, dict) or set(payload) != {"focus"}:
            raise RuntimeError("Local model did not follow the focus schema.")
        focus = payload.get("focus")
        if focus not in SUPPORTED_FOCUS:
            raise RuntimeError("Local model returned an unsupported review focus.")
        return focus

    @staticmethod
    def _validate_finding(finding: dict) -> None:
        required = ("finding_id", "row_number", "rule_id", "field", "observed", "expected", "status")
        if any(key not in finding for key in required):
            raise ValueError("Finding evidence is incomplete.")
        for key in required:
            value = finding[key]
            if isinstance(value, str) and len(value) > 200:
                raise ValueError("Finding text is too long for the bounded explanation workflow.")

    def _result(self, finding: dict, *, intent: str, focus: str | None, text: str,
                elapsed: float, digest: str | None, routing_source: str,
                model_invoked: bool) -> dict:
        return {
            "text": text,
            "model": self.model,
            "digest": digest,
            "elapsed_seconds": round(elapsed, 2),
            "finding_id": finding["finding_id"],
            "rule_id": finding["rule_id"],
            "record_ordinal": finding["row_number"],
            "observed": finding["observed"],
            "expected": finding["expected"],
            "intent": intent,
            "focus": focus,
            "routing_source": routing_source,
            "model_invoked": model_invoked,
            "notice": (
                "The deterministic scope guard rejected an unrelated question; no model inference ran. "
                "No review decision was saved."
                if not model_invoked
                else
                "Scope was decided deterministically; local AI classified only the review focus. "
                "Factual wording was assembled from verified evidence. No review decision was saved."
            ),
        }

    def explain(self, summary: dict, finding: dict, question: str) -> dict:
        del summary
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 600:
            raise ValueError("Use a question of 1–600 characters.")
        self._validate_finding(finding)

        intent = scope_guard(question)
        if intent == "out_of_scope":
            return self._result(
                finding, intent=intent, focus=None, text=_decline_text(finding),
                elapsed=0.0, digest=None, routing_source="deterministic_scope_guard",
                model_invoked=False,
            )

        models = self._request("GET", "/api/tags").get("models", [])
        match = next((m for m in models if m.get("name") == self.model), None)
        if not match:
            raise ValueError("Model is not installed under that exact name. Check ollama list first.")
        details = self._request("POST", "/api/show", {"model": self.model})
        if (match.get("remote_host") or match.get("remote_model") or details.get("remote_host")
                or details.get("remote_model") or not details.get("model_info")):
            raise ValueError("Remote or unverified model metadata rejected.")

        started = time.monotonic()
        answer = self._request("POST", "/api/chat", {
            "model": self.model,
            "stream": False,
            "keep_alive": "5m",
            "format": FOCUS_FORMAT,
            "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 24},
            "messages": [
                {"role": "system", "content": FOCUS_SYSTEM},
                {"role": "user", "content": question.strip()},
            ],
        })
        message = answer.get("message", {})
        raw = message.get("content", "")
        if (answer.get("done") is not True or message.get("tool_calls")
                or not isinstance(raw, str) or not raw.strip() or len(raw) > 1000):
            raise RuntimeError("Local model did not return a usable review focus.")
        try:
            focus = self._validate_focus(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Local model did not return valid structured JSON.") from exc

        return self._result(
            finding, intent="in_scope", focus=focus, text=grounded_text(finding),
            elapsed=time.monotonic() - started, digest=match.get("digest"),
            routing_source="local_model_focus", model_invoked=True,
        )
