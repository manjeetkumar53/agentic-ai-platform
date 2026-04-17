from __future__ import annotations

from app.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, cheap_model: str = "gpt-4o-mini") -> None:
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise ImportError("openai package required: pip install openai") from exc
        self._client = OpenAI()
        self._model = cheap_model

    def complete(self, prompt: str, context: str) -> tuple[str, int, int]:
        merged = f"{context}\n\nUser prompt: {prompt}".strip()
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": merged}],
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        return content, usage.prompt_tokens, usage.completion_tokens
