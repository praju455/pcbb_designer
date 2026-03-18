"""Ollama-backed LLM provider implementation."""

from __future__ import annotations

import json
from typing import Any

import requests
from rich.console import Console

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError


class OllamaLLMProvider(BaseLLMProvider):
    """Generate completions using a local Ollama server."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the provider from configuration."""

        self._settings = get_settings()
        self._console = console or Console(stderr=True)

    def _check_running(self) -> None:
        """Ensure the Ollama daemon is reachable."""

        try:
            response = requests.get(f"{self._settings.ollama_base_url}/api/tags", timeout=3)
        except requests.RequestException as exc:
            raise LLMProviderError("Ollama not running. Start with: ollama serve") from exc
        if response.status_code >= 400:
            raise LLMProviderError("Ollama not running. Start with: ollama serve")

    def _generate(self, prompt: str, system: str | None = None) -> str:
        """Call the Ollama generate endpoint."""

        self._check_running()
        payload: dict[str, Any] = {
            "model": self._settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        with self._console.status(
            f"[bold cyan]Waiting for Ollama ({self._settings.ollama_model})[/bold cyan]", spinner="dots"
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

        content = response.json().get("response", "").strip()
        if not content:
            raise LLMProviderError("Ollama returned an empty response.")
        return content

    def generate(self, prompt: str) -> str:
        """Generate plain text from a user prompt."""

        return self._generate(prompt)

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON conforming to a schema, retrying on parse failures."""

        system_prompt = (
            "You are a precise JSON generator. Return only valid JSON that conforms to the provided schema. "
            "Do not use markdown fences or explanatory text."
        )
        schema_text = json.dumps(schema, indent=2)
        last_error: Exception | None = None

        for attempt in range(1, 4):
            raw = self._generate(f"{prompt}\n\nJSON schema:\n{schema_text}\n\nAttempt: {attempt}", system=system_prompt)
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise LLMProviderError(f"Ollama did not return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "ollama"
