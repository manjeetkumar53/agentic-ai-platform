from __future__ import annotations

from tests.conftest import client


def test_metrics_summary_endpoint_updates() -> None:
    before = client.get("/v1/metrics/summary")
    assert before.status_code == 200
    before_count = before.json()["request_count"]

    run = client.post("/v1/agent/run", json={"prompt": "Measure this request"})
    assert run.status_code == 200

    after = client.get("/v1/metrics/summary")
    assert after.status_code == 200
    payload = after.json()
    assert payload["request_count"] >= before_count + 1
    assert "by_provider" in payload


def test_circuit_breaker_status_endpoint() -> None:
    resp = client.get("/v1/circuit-breaker/status")
    assert resp.status_code == 200
    assert resp.json()["state"] in {"closed", "open", "half_open"}
