# Agentic AI Platform

A production-style agentic AI platform built in 7 days, demonstrating the complete engineering stack needed to ship a reliable, observable, and safe multi-agent system.

![Agent Request Flow](assets/demo/agent-flow.gif)

---

## Why this exists

Most "agent" demos are wrappers around a single LLM call. This repo shows what comes next: **planning, tool execution, reliability, observability, safety guardrails, and evaluation** — the layers that matter in production.

---

## Architecture

```
┌──────────┐   POST /v1/agent/run   ┌──────────────────────────────────────────────┐
│  Client  │ ─────────────────────► │           FastAPI Application                │
└──────────┘                        │                                              │
                                    │  RequestLoggingMiddleware                    │
                                    │    X-Request-ID  ·  X-Latency-MS            │
                                    │                                              │
                                    │  ┌──────────┐   ┌──────────────────────┐    │
                                    │  │ Guardrails│   │  AgentPlatformService│    │
                                    │  │ PIIGuard  │──►│                      │    │
                                    │  │ Allowlist │   │  PlannerAgent        │    │
                                    │  │ RespGuard │   │    ↓                 │    │
                                    │  └──────────┘   │  ExecutorAgent        │    │
                                    │                  │    ↓ tools            │    │
                                    │                  │  LLMProvider          │    │
                                    │                  │    ↓ circuit breaker  │    │
                                    │                  │  TelemetryStore (SQL) │    │
                                    │                  └──────────────────────┘    │
                                    └──────────────────────────────────────────────┘
```

### Layer summary

| Layer | File | What it does |
|---|---|---|
| **Middleware** | `app/middleware.py` | Injects `X-Request-ID`, measures latency, structured JSON logs |
| **Guardrails** | `app/guardrails.py` | PII scan, tool allowlist, response length/phrase enforcement |
| **Planner** | `app/orchestration.py` | Keyword/numeric detection → selects tool set |
| **Executor** | `app/orchestration.py` | Runs tools, assembles context blob |
| **Tools** | `app/tools/` | Calculator (AST-safe), SearchDocs (in-memory keyword) |
| **Provider** | `app/providers/` | Protocol + factory: mock, OpenAI, Ollama, Anthropic |
| **Reliability** | `app/reliability.py` | Circuit breaker (CLOSED/OPEN/HALF_OPEN) + retry with backoff |
| **Telemetry** | `app/telemetry.py` | SQLite-backed event store, AVG/SUM summary queries |
| **Memory** | `app/memory.py` | In-memory session facts |
| **Evaluation** | `evaluation/run.py` | F1/precision/recall/exact-match harness, CI gate |
| **Dashboard** | `dashboard/app.py` | Streamlit real-time analytics with Plotly charts |

---

## Quick start

```bash
git clone https://github.com/manjeetkumar53/agentic-ai-platform.git
cd agentic-ai-platform

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive Swagger UI.

### Analytics dashboard

```bash
streamlit run dashboard/app.py
```

### Planner evaluation

```bash
python -m evaluation.run
```

---

## Configuration

Copy `.env.example` and adjust:

```env
MODEL_PROVIDER=mock          # mock | ollama | openai | anthropic
INPUT_PRICE_PER_1M=0.15
OUTPUT_PRICE_PER_1M=0.60
MAX_ATTEMPTS=2
BREAKER_FAILURE_THRESHOLD=3
BREAKER_RECOVERY_TIMEOUT_S=15
TELEMETRY_DB=telemetry.db
```

### Switching providers

| Provider | Env | Notes |
|---|---|---|
| `mock` | — | Default, deterministic, zero latency |
| `ollama` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Requires local `ollama serve` |
| `openai` | `OPENAI_API_KEY` | Requires `pip install openai` |
| `anthropic` | `ANTHROPIC_API_KEY` | Requires `pip install anthropic` |

---

## API Reference

### `POST /v1/agent/run`

```json
{
  "prompt": "What is 128 * 7 using CQRS context?",
  "session_id": "optional-session-id"
}
```

**Response:**

```json
{
  "request_id": "3fa85f64-...",
  "answer": "The result is 896.",
  "trace": {
    "planner_reasoning": "Detected numeric intent; Detected architecture/docs lookup intent",
    "selected_tools": ["calculator", "search_docs"],
    "tool_calls": [
      { "tool_name": "calculator", "tool_input": "128 * 7", "tool_output": "896" }
    ]
  },
  "latency_ms": 4.2,
  "tokens_in": 120,
  "tokens_out": 35,
  "estimated_cost_usd": 0.0000327,
  "provider": "mock",
  "fallback_used": false
}
```

**Guardrail violation (HTTP 422):**

```json
{
  "error": "guardrail_violation",
  "guard": "PIIGuard",
  "detail": "Detected email pattern in prompt — request blocked"
}
```

### `GET /v1/metrics/summary`

Returns aggregate runtime metrics: `request_count`, `avg_latency_ms`, `avg_cost_usd`, `total_cost_usd`, `fallback_count`, `by_provider`.

### `GET /v1/circuit-breaker/status`

Returns `{ "state": "CLOSED" }`. States: `CLOSED` → `OPEN` → `HALF_OPEN`.

### `GET /v1/eval/events?limit=100`

Returns raw telemetry events as `{ "events": [...] }`.

---

## Guardrails

| Guard | Trigger | Action |
|---|---|---|
| **PIIGuard** | Email, phone, SSN, credit card, IPv4 in prompt | HTTP 422, request blocked |
| **ToolAllowlist** | Session requests a tool not in its allowlist | HTTP 422, request blocked |
| **ResponseGuard** | Response too long or contains blocked phrases | HTTP 422, response suppressed |

PIIGuard also exposes `redact()` — replaces sensitive tokens with `[REDACTED-TYPE]` placeholders.

---

## Reliability

- **CircuitBreaker** — CLOSED → OPEN after N failures, auto-probes, returns to CLOSED on success
- **Retry with backoff** — configurable max attempts and initial delay
- **Fallback** — silent fallback to `MockLLMProvider` on provider failure; `fallback_used: true` in response

---

## Planner evaluation

```
python -m evaluation.run

=== Planner Evaluation Report ===
Elapsed: 0.66 ms  |  Samples: 15

Overall:
  precision       1.0000
  recall          1.0000
  f1              1.0000
  exact_match     1.0000

By category:
  arithmetic     exact=1.00  f1=1.00  n=5
  docs           exact=1.00  f1=1.00  n=5
  multi-tool     exact=1.00  f1=1.00  n=2
  direct         exact=1.00  f1=1.00  n=3
```

CI gates on F1 ≥ 0.80 — exit code 1 if regression detected.

---

## Tests

```bash
pytest -q          # 54 tests
```

| Module | Tests | Coverage |
|---|---|---|
| `test_health.py` | 1 | /health endpoint |
| `test_orchestrator.py` | 5 | planner paths, tool calls, fallback injection |
| `test_metrics.py` | 4 | telemetry, events, X-Request-ID, circuit breaker |
| `test_evaluation.py` | 13 | metric helpers, integration against benchmark dataset |
| `test_dashboard.py` | 6 | fetch helpers (offline mocking) |
| `test_guardrails.py` | 20 | PII patterns, allowlist, response guard, HTTP 422 |

---

## Project structure

```
agentic-ai-platform/
├── app/
│   ├── config.py          # Settings dataclass (env vars)
│   ├── guardrails.py      # PIIGuard, ToolAllowlist, ResponseGuard
│   ├── main.py            # FastAPI app, routes, exception handlers
│   ├── memory.py          # In-memory session store
│   ├── middleware.py      # X-Request-ID + latency logging
│   ├── models.py          # Pydantic request/response models
│   ├── orchestration.py   # PlannerAgent, ExecutorAgent, AgentPlatformService
│   ├── reliability.py     # CircuitBreaker, retry_with_backoff
│   ├── telemetry.py       # TelemetryStore (SQLite), TelemetryEvent
│   ├── providers/         # LLMProvider protocol + mock/openai/ollama/anthropic
│   └── tools/             # calculator, search_docs, base protocol
├── dashboard/
│   └── app.py             # Streamlit analytics dashboard
├── evaluation/
│   ├── prompts.json       # 15 labeled benchmark prompts
│   └── run.py             # Precision/recall/F1 harness with CLI
├── scripts/
│   └── generate_demo_assets.py   # Playwright screenshots + Pillow GIF
├── tests/
│   ├── conftest.py
│   ├── test_dashboard.py
│   ├── test_evaluation.py
│   ├── test_guardrails.py
│   ├── test_health.py
│   ├── test_metrics.py
│   └── test_orchestrator.py
└── assets/
    ├── demo/agent-flow.gif
    └── screenshots/
```

---

## Build log

| Day | Commit | What shipped |
|-----|--------|--------------|
| 1 | `fa2cacf` | FastAPI scaffold, Planner→Executor flow, mock provider, tools, session memory, 5 tests |
| 2 | `2fe8f6f` | Provider factory (mock/OpenAI/Ollama/Anthropic), circuit breaker, retry, telemetry, 8 tests |
| 3 | `b435236` | SQLite telemetry, RequestLoggingMiddleware, X-Request-ID, /eval/events, 10 tests |
| 4 | `1cffb53` | Planner evaluation harness, 15-prompt benchmark, F1/precision/recall, CI gate, 23 tests |
| 5 | `40a2a10` | Streamlit analytics dashboard (8 charts, auto-refresh, provider table), 29 tests |
| 6 | `41feaf4` | Guardrails (PIIGuard, ToolAllowlist, ResponseGuard), HTTP 422 handler, 54 tests |
| 7 | — | README polish, architecture diagram, agent-flow GIF, screenshot script |

---

## Stack

- **Python 3.13** / **FastAPI 0.116** / **Pydantic v2**
- **SQLite** (stdlib) — zero-dependency telemetry persistence
- **Streamlit + Plotly + pandas** — analytics dashboard
- **Playwright + Pillow** — screenshot and GIF generation
- **pytest + httpx** — isolated temp DB per test session
