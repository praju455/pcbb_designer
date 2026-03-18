"""Ollama local provider implementation."""

from __future__ import annotations

import json
from typing import Any

import requests
from rich.console import Console

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError


class OllamaLLMProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama daemon."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the Ollama provider."""

        self._settings = get_settings()
        self._console = console or Console(stderr=True)

    def _ensure_running(self) -> None:
        """Ensure the Ollama daemon is available."""

        try:
            response = requests.get(f"{self._settings.ollama_base_url}/api/tags", timeout=3)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LLMProviderError("Ollama not running. Run: ollama serve") from exc

    def _complete(self, prompt: str, system: str | None = None) -> str:
        """Execute a local generation request."""

        self._ensure_running()
        payload: dict[str, Any] = {
            "model": self._settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        with self._console.status(
            f"[bold cyan]Ollama generating with {self._settings.ollama_model}[/bold cyan]",
            spinner="dots",
        ):
            try:
                response = requests.post(
                    f"{self._settings.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        text = response.json().get("response", "").strip()
        if not text:
            raise LLMProviderError("Ollama returned an empty response.")
        return text

    def generate(self, prompt: str) -> str:
        """Generate plain text."""

        return self._complete(prompt)

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate schema-shaped JSON, retrying on parse failures."""

        schema_text = json.dumps(schema, indent=2)
        system = "Return only valid JSON matching the provided schema."
        last_error: Exception | None = None

        for attempt in range(1, 4):
            raw = self._complete(f"{prompt}\n\nSchema:\n{schema_text}\n\nAttempt {attempt} of 3.", system=system)
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise LLMProviderError(f"Ollama failed to return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "ollama"

    def test_connection(self) -> bool:
        """Return whether Ollama is reachable."""

        self._ensure_running()
        return True
