from __future__ import annotations

from app.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-haiku-4-5") -> None:
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise ImportError("anthropic package required: pip install anthropic") from exc
        self._client = anthropic.Anthropic()
        self._model = model

    def complete(self, prompt: str, context: str) -> tuple[str, int, int]:
        merged = f"{context}\n\nUser prompt: {prompt}".strip()
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": merged}],
        )
        content = message.content[0].text if message.content else ""
        return content, message.usage.input_tokens, message.usage.output_tokens
