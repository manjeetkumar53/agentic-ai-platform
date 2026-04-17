from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import Lock


@dataclass
class TelemetryEvent:
    request_id: str
    created_at: str
    provider: str
    latency_ms: float
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float
    fallback_used: bool
    tool_count: int


class TelemetryStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    request_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    tokens_in INTEGER NOT NULL,
                    tokens_out INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    fallback_used INTEGER NOT NULL,
                    tool_count INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def add(self, event: TelemetryEvent) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO telemetry_events (
                        request_id,
                        created_at,
                        provider,
                        latency_ms,
                        tokens_in,
                        tokens_out,
                        estimated_cost_usd,
                        fallback_used,
                        tool_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.request_id,
                        event.created_at,
                        event.provider,
                        event.latency_ms,
                        event.tokens_in,
                        event.tokens_out,
                        event.estimated_cost_usd,
                        int(event.fallback_used),
                        event.tool_count,
                    ),
                )
                conn.commit()

    def all_events(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT request_id, created_at, provider, latency_ms, tokens_in, tokens_out,
                       estimated_cost_usd, fallback_used, tool_count
                FROM telemetry_events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "request_id": row[0],
                "created_at": row[1],
                "provider": row[2],
                "latency_ms": row[3],
                "tokens_in": row[4],
                "tokens_out": row[5],
                "estimated_cost_usd": row[6],
                "fallback_used": bool(row[7]),
                "tool_count": row[8],
            }
            for row in rows
        ]

    def summary(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]
            if total == 0:
                return {
                    "request_count": 0,
                    "avg_latency_ms": 0.0,
                    "avg_cost_usd": 0.0,
                    "total_cost_usd": 0.0,
                    "fallback_count": 0,
                    "by_provider": {},
                }

            avg_latency_ms, avg_cost_usd, total_cost_usd, fallback_count = conn.execute(
                """
                SELECT
                    AVG(latency_ms),
                    AVG(estimated_cost_usd),
                    SUM(estimated_cost_usd),
                    SUM(fallback_used)
                FROM telemetry_events
                """
            ).fetchone()

            by_provider_rows = conn.execute(
                "SELECT provider, COUNT(*) FROM telemetry_events GROUP BY provider"
            ).fetchall()

        return {
            "request_count": int(total),
            "avg_latency_ms": round(float(avg_latency_ms or 0.0), 2),
            "avg_cost_usd": round(float(avg_cost_usd or 0.0), 8),
            "total_cost_usd": round(float(total_cost_usd or 0.0), 8),
            "fallback_count": int(fallback_count or 0),
            "by_provider": {str(provider): int(count) for provider, count in by_provider_rows},
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
