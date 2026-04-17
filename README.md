# Agentic AI Platform

An API-first agentic AI reference implementation focused on orchestration, tool execution, guardrails, reliability patterns, telemetry, evaluation, and operational dashboards.

![Agent Request Flow](assets/demo/agent-flow.gif)

---

## Why this exists

Most "agent" demos stop at a single model call. Real systems require more:

- deterministic orchestration and tool invocation traces
- resilient provider behavior under failure
- safety and policy enforcement before and after generation
- observability for latency, cost, fallback rate, and provider mix
- evaluation harnesses to catch planner regressions over time

This repository is built to showcase those production concerns end-to-end.

## At a glance

| Capability | Production behavior |
|---|---|
| Multi-agent orchestration | Planner -> Executor -> Provider flow with explicit trace objects |
| Reliability | Circuit breaker + retries + fallback provider |
| Safety | Prompt and response guardrails with structured violation responses |
| Observability | Request IDs, latency headers, SQLite telemetry, metrics endpoints |
| Evaluation | Benchmark runner with precision/recall/F1 and CI threshold gating |
| Operations UI | Streamlit analytics dashboard for runtime monitoring |

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

## Local run modes

### API only

```bash
uvicorn app.main:app --reload
```

### API + dashboard

```bash
# terminal 1
uvicorn app.main:app --reload

# terminal 2
streamlit run dashboard/app.py
```

### API with Ollama provider

```bash
# terminal 1
ollama serve

# terminal 2
MODEL_PROVIDER=ollama uvicorn app.main:app --reload
```

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

Returns `{ "state": "closed" }`. States: `closed` -> `open` -> `half_open`.

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

## Operational endpoints

- `GET /health`: liveness check
- `GET /v1/metrics/summary`: aggregate request, latency, cost, fallback metrics
- `GET /v1/eval/events?limit=100`: recent event stream
- `GET /v1/circuit-breaker/status`: current reliability state

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

## How to test

### 1. Fast smoke test (manual API validation)

Start the API:

```bash
uvicorn app.main:app --reload
```

Run these checks:

```bash
# health
curl -s http://127.0.0.1:8000/health

# normal request
curl -s -X POST http://127.0.0.1:8000/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is 42 * 7?"}'

# guardrail violation (expects HTTP 422)
curl -s -X POST http://127.0.0.1:8000/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"prompt":"email me at demo@example.com"}'

# telemetry and breaker
curl -s http://127.0.0.1:8000/v1/metrics/summary
curl -s http://127.0.0.1:8000/v1/circuit-breaker/status
curl -s "http://127.0.0.1:8000/v1/eval/events?limit=5"
```

### 2. Automated test suite

```bash
pytest -q
```

Expected outcome: all tests pass.

### 3. Run only critical suites

```bash
# orchestration + reliability behavior
pytest -q tests/test_orchestrator.py tests/test_metrics.py

# guardrail policy coverage
pytest -q tests/test_guardrails.py

# dashboard fetch helper behavior
pytest -q tests/test_dashboard.py
```

### 4. Planner regression benchmark

```bash
python -m evaluation.run
```

This prints precision/recall/F1/exact-match and exits non-zero if quality drops below threshold.

### 5. Dashboard verification

```bash
# terminal 1
uvicorn app.main:app --reload

# terminal 2
streamlit run dashboard/app.py
```

In the dashboard, validate:

- request count increases after API calls
- provider mix and latency charts update
- fallback count remains stable unless forced failures are introduced
- circuit breaker badge reflects runtime state

### Test coverage map

| Module | Focus area |
|---|---|
| `test_health.py` | service liveness endpoint |
| `test_orchestrator.py` | planning, tool calls, memory interaction, fallback path |
| `test_metrics.py` | summary/event endpoints, request ID propagation, breaker status |
| `test_evaluation.py` | metric math + benchmark dataset integration |
| `test_dashboard.py` | dashboard data fetch helpers (offline mocks) |
| `test_guardrails.py` | PII detection, allowlists, response constraints, HTTP 422 behavior |

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

## Milestones

| Milestone | Commit | What shipped |
|-----|--------|--------------|
| Core API and orchestration | `fa2cacf` | FastAPI scaffold, Planner→Executor flow, mock provider, tools, session memory, tests |
| Provider abstraction and resilience | `2fe8f6f` | Provider factory (mock/OpenAI/Ollama/Anthropic), circuit breaker, retry, telemetry |
| Persistent telemetry and request tracing | `b435236` | SQLite telemetry, RequestLoggingMiddleware, X-Request-ID, /eval/events |
| Planner evaluation harness | `1cffb53` | 15-prompt benchmark, precision/recall/F1/exact-match metrics, CI quality gate |
| Runtime analytics dashboard | `40a2a10` | Streamlit dashboard with latency/cost/provider/fallback views |
| Guardrails and policy handling | `41feaf4` | PIIGuard, ToolAllowlist, ResponseGuard, HTTP 422 violation handling |
| Documentation and demo assets | `3136321` | README upgrade, architecture diagram, flow GIF, asset generation script |

---

## Stack

- **Python 3.13** / **FastAPI 0.116** / **Pydantic v2**
- **SQLite** (stdlib) — zero-dependency telemetry persistence
- **Streamlit + Plotly + pandas** — analytics dashboard
- **Playwright + Pillow** — screenshot and GIF generation
- **pytest + httpx** — isolated temp DB per test session
