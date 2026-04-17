from __future__ import annotations

import time
import uuid

from app.config import Settings
from app.memory import SessionMemoryStore
from app.models import AgentRunResponse, AgentTrace, ExecutionResult, PlannerOutput, ToolCall
from app.providers.factory import create_provider
from app.providers.mock_llm import MockLLMProvider
from app.reliability import CircuitBreaker, CircuitBreakerOpen, retry_with_backoff
from app.telemetry import InMemoryTelemetryStore, TelemetryEvent
from app.tools.calculator import CalculatorTool
from app.tools.search_docs import SearchDocsTool


class PlannerAgent:
    def plan(self, prompt: str) -> PlannerOutput:
        lowered = prompt.lower()
        tools: list[str] = []
        reasoning_bits: list[str] = []

        if any(ch.isdigit() for ch in prompt):
            tools.append("calculator")
            reasoning_bits.append("Detected numeric intent")

        if any(term in lowered for term in ["cqrs", "event", "vector", "latency"]):
            tools.append("search_docs")
            reasoning_bits.append("Detected architecture/docs lookup intent")

        if not tools:
            reasoning_bits.append("No tool needed; answer directly")

        return PlannerOutput(reasoning="; ".join(reasoning_bits), tools=tools)


class ExecutorAgent:
    def __init__(self) -> None:
        self._registry = {
            "calculator": CalculatorTool(),
            "search_docs": SearchDocsTool(),
        }

    def execute(self, prompt: str, tools: list[str]) -> ExecutionResult:
        calls: list[ToolCall] = []
        context_parts: list[str] = []

        for tool_name in tools:
            tool = self._registry.get(tool_name)
            if tool is None:
                continue
            output = tool.run(prompt)
            calls.append(ToolCall(tool_name=tool_name, tool_input=prompt, tool_output=output))
            context_parts.append(f"[{tool_name}] {output}")

        return ExecutionResult(tool_calls=calls, context_blob="\n".join(context_parts))


class AgentPlatformService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._planner = PlannerAgent()
        self._executor = ExecutorAgent()
        self._llm = create_provider(settings.model_provider)
        self._fallback_llm = MockLLMProvider()
        self._memory = SessionMemoryStore()
        self._telemetry = InMemoryTelemetryStore()
        self._breaker = CircuitBreaker(
            failure_threshold=settings.breaker_failure_threshold,
            recovery_timeout_s=settings.breaker_recovery_timeout_s,
        )

    def metrics_summary(self) -> dict:
        return self._telemetry.summary()

    def breaker_state(self) -> str:
        return self._breaker.state.value

    def run(self, prompt: str, session_id: str | None = None) -> AgentRunResponse:
        t0 = time.perf_counter()
        request_id = str(uuid.uuid4())
        sid = session_id or "default"

        memory = self._memory.read(sid)
        planner_output = self._planner.plan(prompt)
        execution = self._executor.execute(prompt, planner_output.tools)
        fallback_used = False
        provider_name = self._llm.name

        context_blob = execution.context_blob
        if memory.facts:
            context_blob = f"memory={memory.facts}\n{context_blob}".strip()

        try:
            answer, tokens_in, tokens_out = retry_with_backoff(
                self._breaker.call,
                self._llm.complete,
                prompt,
                context_blob,
                max_attempts=self._settings.max_attempts,
            )
        except (CircuitBreakerOpen, Exception):
            fallback_used = True
            provider_name = self._fallback_llm.name
            answer, tokens_in, tokens_out = self._fallback_llm.complete(
                prompt=prompt,
                context=context_blob,
            )

        self._memory.upsert(sid, {"last_prompt": prompt, "last_tools": planner_output.tools})

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        estimated_cost_usd = round(
            (
                (tokens_in * self._settings.input_price_per_1m)
                + (tokens_out * self._settings.output_price_per_1m)
            )
            / 1_000_000,
            8,
        )

        self._telemetry.add(
            TelemetryEvent(
                request_id=request_id,
                provider=provider_name,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=estimated_cost_usd,
                fallback_used=fallback_used,
                tool_count=len(execution.tool_calls),
            )
        )

        return AgentRunResponse(
            request_id=request_id,
            answer=answer,
            trace=AgentTrace(
                planner_reasoning=planner_output.reasoning,
                selected_tools=planner_output.tools,
                tool_calls=execution.tool_calls,
            ),
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=estimated_cost_usd,
            provider=provider_name,
            fallback_used=fallback_used,
        )
