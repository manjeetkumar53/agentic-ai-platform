from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TelemetryEvent:
    request_id: str
    provider: str
    latency_ms: float
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float
    fallback_used: bool
    tool_count: int


class InMemoryTelemetryStore:
    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    def add(self, event: TelemetryEvent) -> None:
        self._events.append(event)

    def summary(self) -> dict:
        total = len(self._events)
        if total == 0:
            return {
                "request_count": 0,
                "avg_latency_ms": 0.0,
                "avg_cost_usd": 0.0,
                "total_cost_usd": 0.0,
                "fallback_count": 0,
                "by_provider": {},
            }

        by_provider: dict[str, int] = {}
        total_latency = 0.0
        total_cost = 0.0
        fallback_count = 0

        for event in self._events:
            total_latency += event.latency_ms
            total_cost += event.estimated_cost_usd
            fallback_count += int(event.fallback_used)
            by_provider[event.provider] = by_provider.get(event.provider, 0) + 1

        return {
            "request_count": total,
            "avg_latency_ms": round(total_latency / total, 2),
            "avg_cost_usd": round(total_cost / total, 8),
            "total_cost_usd": round(total_cost, 8),
            "fallback_count": fallback_count,
            "by_provider": by_provider,
        }
