from __future__ import annotations

from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider


def create_provider(name: str) -> LLMProvider:
    provider = name.lower()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "ollama":
        return OllamaProvider()
    if provider == "anthropic":
        return AnthropicProvider()
    return MockLLMProvider()
