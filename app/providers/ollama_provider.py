from __future__ import annotations

import os

import httpx

from app.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat")
        self._model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

    def complete(self, prompt: str, context: str) -> tuple[str, int, int]:
        merged = f"{context}\n\nUser prompt: {prompt}".strip()
        response = httpx.post(
            self._base_url,
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": merged}],
                "stream": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["message"]["content"]
        input_tokens = data.get("prompt_eval_count", max(1, len(merged) // 4))
        output_tokens = data.get("eval_count", max(24, len(content) // 4))
        return content, input_tokens, output_tokens
