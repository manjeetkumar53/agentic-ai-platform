from __future__ import annotations

import time
import uuid

from app.memory import SessionMemoryStore
from app.models import AgentRunResponse, AgentTrace, ExecutionResult, PlannerOutput, ToolCall
from app.providers.mock_llm import MockLLMProvider
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
    def __init__(self) -> None:
        self._planner = PlannerAgent()
        self._executor = ExecutorAgent()
        self._llm = MockLLMProvider()
        self._memory = SessionMemoryStore()

    def run(self, prompt: str, session_id: str | None = None) -> AgentRunResponse:
        t0 = time.perf_counter()
        request_id = str(uuid.uuid4())
        sid = session_id or "default"

        memory = self._memory.read(sid)
        planner_output = self._planner.plan(prompt)
        execution = self._executor.execute(prompt, planner_output.tools)

        context_blob = execution.context_blob
        if memory.facts:
            context_blob = f"memory={memory.facts}\n{context_blob}".strip()

        answer, tokens_in, tokens_out = self._llm.complete(prompt=prompt, context=context_blob)

        self._memory.upsert(sid, {"last_prompt": prompt, "last_tools": planner_output.tools})

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        estimated_cost_usd = round(((tokens_in * 0.15) + (tokens_out * 0.60)) / 1_000_000, 8)

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
        )
