from __future__ import annotations

from fastapi import FastAPI

from app.models import AgentRunRequest, AgentRunResponse, HealthResponse
from app.orchestration import AgentPlatformService

app = FastAPI(title="Agentic AI Platform", version="0.1.0")
_service = AgentPlatformService()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/agent/run", response_model=AgentRunResponse)
def run_agent(payload: AgentRunRequest) -> AgentRunResponse:
    return _service.run(prompt=payload.prompt, session_id=payload.session_id)
