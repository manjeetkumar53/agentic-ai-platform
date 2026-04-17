from __future__ import annotations

from app.main import _service
from tests.conftest import client


def test_run_agent_basic() -> None:
    resp = client.post("/v1/agent/run", json={"prompt": "Hello agent"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"]
    assert "answer" in body
    assert body["trace"]["selected_tools"] == []
    assert body["provider"]
    assert body["fallback_used"] is False


def test_run_agent_calculator_path() -> None:
    resp = client.post("/v1/agent/run", json={"prompt": "What is 12*7 + 4?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "calculator" in body["trace"]["selected_tools"]
    assert any(call["tool_name"] == "calculator" for call in body["trace"]["tool_calls"])


def test_run_agent_docs_path() -> None:
    resp = client.post(
        "/v1/agent/run",
        json={"prompt": "Explain CQRS and event sourcing trade-offs"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "search_docs" in body["trace"]["selected_tools"]


def test_session_memory_roundtrip() -> None:
    first = client.post(
        "/v1/agent/run",
        json={"prompt": "Track my preference", "session_id": "s1"},
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/agent/run",
        json={"prompt": "What did I ask before?", "session_id": "s1"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["trace"]["planner_reasoning"]


def test_fallback_when_primary_provider_fails() -> None:
    class BrokenProvider:
        name = "broken"

        def complete(self, prompt: str, context: str) -> tuple[str, int, int]:
            raise RuntimeError("forced failure")

    previous = _service._llm
    _service._llm = BrokenProvider()
    try:
        resp = client.post("/v1/agent/run", json={"prompt": "Force fallback path"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["fallback_used"] is True
        assert body["provider"] == "mock"
    finally:
        _service._llm = previous
