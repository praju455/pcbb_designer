"""LLM provider abstractions and factory helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pcbai.core.config import get_settings


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot fulfill a request."""


class BaseLLMProvider(ABC):
    """Common interface implemented by all LLM backends."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a plain-text completion."""

    @abstractmethod
    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON matching a supplied schema."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return a human-readable provider name."""


class UnsupportedLLMProvider(BaseLLMProvider):
    """Provider used when the configured backend is not implemented."""

    def __init__(self, provider_name: str) -> None:
        """Store the provider that was requested."""

        self._provider_name = provider_name

    def generate(self, prompt: str) -> str:
        """Raise a descriptive error for unsupported backends."""

        raise LLMProviderError(
            f"LLM provider '{self._provider_name}' is not implemented in this repository. "
            "Use 'groq' or 'ollama', or add a provider implementation."
        )

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Raise a descriptive error for unsupported backends."""

        raise LLMProviderError(
            f"LLM provider '{self._provider_name}' is not implemented in this repository. "
            "Use 'groq' or 'ollama', or add a provider implementation."
        )

    def get_provider_name(self) -> str:
        """Return the configured provider name."""

        return self._provider_name


def get_llm_provider() -> BaseLLMProvider:
    """Instantiate the configured LLM backend."""

    settings = get_settings()
    if settings.llm_provider == "groq":
        from pcbai.llm.providers.groq_provider import GroqLLMProvider

        return GroqLLMProvider()
    if settings.llm_provider == "ollama":
        from pcbai.llm.providers.ollama_provider import OllamaLLMProvider

        return OllamaLLMProvider()
    return UnsupportedLLMProvider(settings.llm_provider)
