# Agentic AI Platform

Production-style mini agent platform built to demonstrate planner/executor orchestration, tool calling, memory, and observable traces.

## What this repo proves

- Multi-agent flow: Planner -> Executor -> LLM response composer
- Tool calling with explicit traces
- Session memory hooks
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
- token/cost estimates

## Tests

```bash
pytest -q
```

## Next build steps

- Replace mock provider with OpenAI/Ollama/Anthropic adapters
- Add Redis-backed short-term memory and Postgres-backed long-term memory
- Add guardrails, retries, and circuit breaker around tool/LLM execution
- Add tracing dashboard (latency, token cost, tool success rate)
