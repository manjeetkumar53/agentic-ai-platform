from __future__ import annotations

from fastapi import FastAPI

from app.config import load_settings
from app.models import AgentRunRequest, AgentRunResponse, HealthResponse, MetricsSummary
from app.orchestration import AgentPlatformService

app = FastAPI(title="Agentic AI Platform", version="0.1.0")
_settings = load_settings()
_service = AgentPlatformService(settings=_settings)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/agent/run", response_model=AgentRunResponse)
def run_agent(payload: AgentRunRequest) -> AgentRunResponse:
    return _service.run(prompt=payload.prompt, session_id=payload.session_id)


@app.get("/v1/metrics/summary", response_model=MetricsSummary)
def metrics_summary() -> MetricsSummary:
    return MetricsSummary(**_service.metrics_summary())


@app.get("/v1/circuit-breaker/status")
def circuit_breaker_status() -> dict[str, str]:
    return {"state": _service.breaker_state()}
