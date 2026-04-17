# Agentic AI Platform

Production-style mini agent platform built to demonstrate planner/executor orchestration, tool calling, memory, and observable traces.

## What this repo proves

- Multi-agent flow: Planner -> Executor -> LLM response composer
- Tool calling with explicit traces
- Session memory hooks
- Provider abstraction with env-based selection (`mock`, `ollama`, `openai`, `anthropic`)
- Reliability layer: retry + circuit breaker + fallback to mock provider
- SQLite telemetry with cost/latency/provider summaries
- Request tracing via `X-Request-ID` and `X-Latency-MS` headers
- API-first interface with typed responses
- Test coverage for orchestration paths

## Quick start

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open Swagger at `http://127.0.0.1:8000/docs`.

## Configuration

Copy `.env.example` and adjust values:

```env
MODEL_PROVIDER=mock
INPUT_PRICE_PER_1M=0.15
OUTPUT_PRICE_PER_1M=0.60
MAX_ATTEMPTS=2
BREAKER_FAILURE_THRESHOLD=3
BREAKER_RECOVERY_TIMEOUT_S=15
TELEMETRY_DB=telemetry.db
```

## API

### POST /v1/agent/run

```json
{
  "prompt": "What is 12*7 + 4?",
  "session_id": "demo-session"
}
```

Response includes:

- `request_id`
- `answer`
- `trace.planner_reasoning`
- `trace.selected_tools`
- `trace.tool_calls`
- `latency_ms`
- `tokens_in`, `tokens_out`, `estimated_cost_usd`
- `provider`, `fallback_used`

### GET /v1/metrics/summary

Returns aggregate runtime metrics:

- `request_count`
- `avg_latency_ms`
- `avg_cost_usd`
- `total_cost_usd`
- `fallback_count`
- `by_provider`

### GET /v1/circuit-breaker/status

Returns current breaker state: `closed`, `open`, or `half_open`.

### GET /v1/eval/events?limit=100

Returns recent telemetry events (`request_id`, `provider`, cost, latency, tokens, fallback flag).

## Tests

```bash
pytest -q
```

## Next build steps

- Add Redis-backed short-term memory and Postgres-backed long-term memory
- Add guardrail policies (PII filtering, tool allowlist, response constraints)
- Add structured traces and dashboard for per-step latency/token/tool success
- Add planner quality evaluation harness and regression prompts
