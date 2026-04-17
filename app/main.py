from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import load_settings
from app.guardrails import GuardrailViolation
from app.middleware import RequestLoggingMiddleware, configure_logging
from app.models import AgentRunRequest, AgentRunResponse, HealthResponse, MetricsSummary
from app.orchestration import AgentPlatformService
from app.telemetry import TelemetryStore

configure_logging()
app = FastAPI(title="Agentic AI Platform", version="0.1.0")
app.add_middleware(RequestLoggingMiddleware)

_settings = load_settings()
_telemetry = TelemetryStore(db_path=Path(_settings.telemetry_db))
_service = AgentPlatformService(settings=_settings, telemetry=_telemetry)


@app.exception_handler(GuardrailViolation)
async def guardrail_violation_handler(request: Request, exc: GuardrailViolation) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "guardrail_violation", "guard": exc.guard, "detail": exc.detail},
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/agent/run", response_model=AgentRunResponse)
def run_agent(payload: AgentRunRequest, request: Request) -> AgentRunResponse:
    rid = getattr(request.state, "request_id", None)
    return _service.run(prompt=payload.prompt, session_id=payload.session_id, request_id=rid)


@app.get("/v1/metrics/summary", response_model=MetricsSummary)
def metrics_summary() -> MetricsSummary:
    return MetricsSummary(**_service.metrics_summary())


@app.get("/v1/circuit-breaker/status")
def circuit_breaker_status() -> dict[str, str]:
    return {"state": _service.breaker_state()}


@app.get("/v1/eval/events")
def eval_events(limit: int = 100) -> dict:
    return {"events": _service.events(limit=limit)}
