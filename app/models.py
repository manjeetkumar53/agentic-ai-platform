from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str | None = None


class ToolCall(BaseModel):
    tool_name: str
    tool_input: str
    tool_output: str


class AgentTrace(BaseModel):
    planner_reasoning: str
    selected_tools: list[str]
    tool_calls: list[ToolCall]


class AgentRunResponse(BaseModel):
    request_id: str
    answer: str
    trace: AgentTrace
    latency_ms: float
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float


class HealthResponse(BaseModel):
    status: str


class PlannerOutput(BaseModel):
    reasoning: str
    tools: list[str]


class ExecutionResult(BaseModel):
    tool_calls: list[ToolCall]
    context_blob: str


class StoredMemory(BaseModel):
    session_id: str
    facts: dict[str, Any]
