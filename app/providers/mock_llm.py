from __future__ import annotations


class MockLLMProvider:
    def complete(self, prompt: str, context: str) -> tuple[str, int, int]:
        tokens_in = max(1, (len(prompt) + len(context)) // 4)
        tokens_out = max(24, min(220, len(prompt) // 2))
        answer = (
            "[mock-agent] "
            "Plan executed with available tools. "
            f"Context summary: {context[:280]}"
        )
        return answer, tokens_in, tokens_out
