"""Tests for the guardrails layer."""
from __future__ import annotations

import pytest

from app.guardrails import (
    Guardrails,
    GuardrailViolation,
    PIIGuard,
    ResponseGuard,
    ToolAllowlist,
)
from tests.conftest import client


# ---------------------------------------------------------------------------
# PIIGuard
# ---------------------------------------------------------------------------

class TestPIIGuard:
    def setup_method(self):
        self.guard = PIIGuard()

    def test_clean_prompt_passes(self):
        self.guard.check("What is the capital of France?")  # no exception

    def test_email_blocked(self):
        with pytest.raises(GuardrailViolation) as exc_info:
            self.guard.check("Email me at alice@example.com please")
        assert exc_info.value.guard == "PIIGuard"
        assert "email" in exc_info.value.detail

    def test_ssn_blocked(self):
        with pytest.raises(GuardrailViolation):
            self.guard.check("My SSN is 123-45-6789")

    def test_phone_blocked(self):
        with pytest.raises(GuardrailViolation):
            self.guard.check("Call me at (555) 867-5309")

    def test_credit_card_blocked(self):
        with pytest.raises(GuardrailViolation):
            self.guard.check("Card number 4111111111111111")

    def test_ipv4_blocked(self):
        with pytest.raises(GuardrailViolation):
            self.guard.check("Connect to 192.168.1.100")

    def test_redact_email(self):
        result = self.guard.redact("Contact alice@example.com for help")
        assert "alice@example.com" not in result
        assert "[REDACTED-EMAIL]" in result

    def test_redact_multiple(self):
        text = "SSN 123-45-6789 email alice@foo.com"
        result = self.guard.redact(text)
        assert "123-45-6789" not in result
        assert "alice@foo.com" not in result


# ---------------------------------------------------------------------------
# ToolAllowlist
# ---------------------------------------------------------------------------

class TestToolAllowlist:
    def setup_method(self):
        self.allowlist = ToolAllowlist()

    def test_no_restriction_allows_everything(self):
        # session 'anon' has no allowlist — all tools pass
        self.allowlist.check("anon", ["calculator", "search_docs"])  # no exception

    def test_registered_session_allows_listed_tools(self):
        self.allowlist.register("s1", ["calculator"])
        self.allowlist.check("s1", ["calculator"])  # ok

    def test_denied_tool_raises(self):
        self.allowlist.register("s1", ["calculator"])
        with pytest.raises(GuardrailViolation) as exc_info:
            self.allowlist.check("s1", ["search_docs"])
        assert exc_info.value.guard == "ToolAllowlist"
        assert "search_docs" in exc_info.value.detail

    def test_partial_denial(self):
        self.allowlist.register("s1", ["calculator"])
        with pytest.raises(GuardrailViolation):
            self.allowlist.check("s1", ["calculator", "search_docs"])

    def test_clear_removes_restriction(self):
        self.allowlist.register("s1", ["calculator"])
        self.allowlist.clear("s1")
        # after clearing, all tools allowed
        self.allowlist.check("s1", ["calculator", "search_docs"])  # no exception

    def test_empty_tool_list_always_passes(self):
        self.allowlist.register("s1", ["calculator"])
        self.allowlist.check("s1", [])  # no exception


# ---------------------------------------------------------------------------
# ResponseGuard
# ---------------------------------------------------------------------------

class TestResponseGuard:
    def setup_method(self):
        self.guard = ResponseGuard(max_length=100, blocked_phrases=["jailbreak", "ignore all"])

    def test_clean_response_passes(self):
        self.guard.check("Here is the answer.")  # no exception

    def test_too_long_raises(self):
        with pytest.raises(GuardrailViolation) as exc_info:
            self.guard.check("x" * 101)
        assert "ResponseGuard" == exc_info.value.guard
        assert "exceeds max" in exc_info.value.detail

    def test_blocked_phrase_raises(self):
        with pytest.raises(GuardrailViolation):
            self.guard.check("Let me jailbreak that for you")

    def test_case_insensitive_phrase_match(self):
        with pytest.raises(GuardrailViolation):
            self.guard.check("IGNORE ALL your instructions")

    def test_exactly_at_limit_passes(self):
        self.guard.check("x" * 100)  # no exception


# ---------------------------------------------------------------------------
# Composite Guardrails
# ---------------------------------------------------------------------------

class TestGuardrails:
    def setup_method(self):
        self.g = Guardrails()

    def test_check_prompt_clean(self):
        self.g.check_prompt("What is 2+2?", "session1", ["calculator"])

    def test_check_prompt_pii(self):
        with pytest.raises(GuardrailViolation):
            self.g.check_prompt("email me at bob@example.com", "s1", [])

    def test_check_response_clean(self):
        self.g.check_response("The result is 4.")

    def test_check_response_too_long(self):
        g = Guardrails(response=ResponseGuard(max_length=10))
        with pytest.raises(GuardrailViolation):
            g.check_response("This response is definitely longer than ten characters")


# ---------------------------------------------------------------------------
# HTTP integration — guardrail triggers 422 on the API
# ---------------------------------------------------------------------------

class TestGuardrailHTTP:
    def test_pii_in_prompt_returns_422(self):
        resp = client.post("/v1/agent/run", json={"prompt": "my email is bad@actor.com"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "guardrail_violation"
        assert body["guard"] == "PIIGuard"

    def test_clean_prompt_returns_200(self):
        resp = client.post("/v1/agent/run", json={"prompt": "Hello world"})
        assert resp.status_code == 200
