"""
Guardrails layer for the Agentic AI Platform.

Provides three independent guard types:

1. PIIGuard      — detects PII patterns in prompts before they reach providers
2. ToolAllowlist — enforces per-session allowed tool sets
3. ResponseGuard — validates model responses against length / keyword constraints

All guards raise GuardrailViolation on failure so callers can handle uniformly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


# ---------------------------------------------------------------------------
# Violation type
# ---------------------------------------------------------------------------

class GuardrailViolation(Exception):
    """Raised when a guardrail detects a policy violation."""

    def __init__(self, guard: str, detail: str) -> None:
        self.guard  = guard
        self.detail = detail
        super().__init__(f"[{guard}] {detail}")


# ---------------------------------------------------------------------------
# PII Guard
# ---------------------------------------------------------------------------

# Conservative patterns — match common PII formats without being overly broad.
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email",           re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("phone_us",        re.compile(r"\b(?:\+1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b")),
    ("ssn",             re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card",     re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b")),
    ("ipv4",            re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")),
]


class PIIGuard:
    """Scans text for PII and raises GuardrailViolation if found."""

    def check(self, text: str) -> None:
        for label, pattern in _PII_PATTERNS:
            if pattern.search(text):
                raise GuardrailViolation(
                    "PIIGuard",
                    f"Detected {label} pattern in prompt — request blocked",
                )

    def redact(self, text: str) -> str:
        """Return text with PII replaced by [REDACTED-<type>] tokens."""
        result = text
        for label, pattern in _PII_PATTERNS:
            result = pattern.sub(f"[REDACTED-{label.upper()}]", result)
        return result


# ---------------------------------------------------------------------------
# Tool Allowlist
# ---------------------------------------------------------------------------

# Default allow-all sentinel — when None, all tools are permitted.
_ALLOW_ALL: frozenset[str] | None = None


@dataclass
class ToolAllowlist:
    """Enforces which tools a session may use.

    If no allowlist is registered for a session, all tools are permitted.
    """

    _session_allowlists: dict[str, frozenset[str]] = field(default_factory=dict)

    def register(self, session_id: str, allowed_tools: list[str]) -> None:
        self._session_allowlists[session_id] = frozenset(allowed_tools)

    def clear(self, session_id: str) -> None:
        self._session_allowlists.pop(session_id, None)

    def check(self, session_id: str, requested_tools: list[str]) -> None:
        allowed = self._session_allowlists.get(session_id)
        if allowed is None:
            return  # no restriction registered
        denied = [t for t in requested_tools if t not in allowed]
        if denied:
            raise GuardrailViolation(
                "ToolAllowlist",
                f"Session '{session_id}' is not permitted to use tools: {denied}",
            )


# ---------------------------------------------------------------------------
# Response Guard
# ---------------------------------------------------------------------------

@dataclass
class ResponseGuard:
    """Validates LLM responses against configurable constraints."""

    max_length: int = 8_000          # characters
    blocked_phrases: list[str] = field(default_factory=list)

    def check(self, response: str) -> None:
        if len(response) > self.max_length:
            raise GuardrailViolation(
                "ResponseGuard",
                f"Response length {len(response)} exceeds max {self.max_length}",
            )
        lower = response.lower()
        for phrase in self.blocked_phrases:
            if phrase.lower() in lower:
                raise GuardrailViolation(
                    "ResponseGuard",
                    f"Response contains blocked phrase: '{phrase}'",
                )


# ---------------------------------------------------------------------------
# Composite facade
# ---------------------------------------------------------------------------

@dataclass
class Guardrails:
    """Single entry-point for all guard checks.

    Usage in service layer::

        guard = Guardrails()
        guard.check_prompt(prompt, session_id, planned_tools)
        # … call LLM …
        guard.check_response(answer)
    """

    pii:        PIIGuard       = field(default_factory=PIIGuard)
    allowlist:  ToolAllowlist  = field(default_factory=ToolAllowlist)
    response:   ResponseGuard  = field(default_factory=ResponseGuard)

    def check_prompt(
        self,
        prompt: str,
        session_id: str,
        planned_tools: list[str],
    ) -> None:
        self.pii.check(prompt)
        self.allowlist.check(session_id, planned_tools)

    def check_response(self, response: str) -> None:
        self.response.check(response)
