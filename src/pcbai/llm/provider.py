"""LLM provider abstractions and factory helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pcbai.core.config import get_settings


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot satisfy a request."""


class BaseLLMProvider(ABC):
    """Common interface implemented by all LLM backends."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate plain text for a prompt."""

    @abstractmethod
    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON that conforms to a supplied schema."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return whether the provider can be reached successfully."""


def get_llm_provider(name: str) -> BaseLLMProvider:
    """Return a concrete provider for the supplied provider name."""

    normalized = name.strip().lower()
    if normalized == "groq":
        from pcbai.llm.providers.groq_provider import GroqLLMProvider

        return GroqLLMProvider()
    if normalized == "gemini":
        from pcbai.llm.providers.gemini_provider import GeminiLLMProvider

        return GeminiLLMProvider()
    if normalized == "ollama":
        from pcbai.llm.providers.ollama_provider import OllamaLLMProvider

        return OllamaLLMProvider()
    raise LLMProviderError(f"Unsupported LLM provider '{name}'. Expected groq, gemini, or ollama.")


def get_generator_llm() -> BaseLLMProvider:
    """Return the configured generator provider."""

    settings = get_settings()
    return get_llm_provider(settings.generator_llm)


def get_verifier_llm() -> BaseLLMProvider:
    """Return the configured verifier provider."""

    settings = get_settings()
    return get_llm_provider(settings.verifier_llm)
