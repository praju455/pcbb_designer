"""Gemini provider implementation."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError


class GeminiLLMProvider(BaseLLMProvider):
    """LLM provider backed by Google Gemini Flash."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the Gemini SDK client."""

        settings = get_settings()
        if not settings.gemini_api_key:
            raise LLMProviderError("GEMINI_API_KEY is not set. Add it to .env before using Gemini.")
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise LLMProviderError("The google-generativeai package is not installed. Run pip install -e .") from exc

        genai.configure(api_key=settings.gemini_api_key)
        self._genai = genai
        self._settings = settings
        self._console = console or Console(stderr=True)
        self._model = genai.GenerativeModel(settings.gemini_model)

    def _complete(self, prompt: str) -> str:
        """Execute a completion request."""

        with self._console.status(
            f"[bold cyan]Gemini verifying with {self._settings.gemini_model}[/bold cyan]",
            spinner="dots",
        ):
            try:
                response = self._model.generate_content(prompt)
            except Exception as exc:  # pragma: no cover - network dependent
                raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        text = getattr(response, "text", "") or ""
        if not text.strip():
            raise LLMProviderError("Gemini returned an empty response.")
        return text.strip()

    def generate(self, prompt: str) -> str:
        """Generate plain text."""

        return self._complete(prompt)

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate schema-shaped JSON, retrying on parse failures."""

        schema_text = json.dumps(schema, indent=2)
        json_prompt = (
            "Return only valid JSON. Do not include markdown or extra commentary.\n\n"
            f"Schema:\n{schema_text}\n\nTask:\n{prompt}"
        )
        last_error: Exception | None = None

        for _attempt in range(3):
            raw = self._complete(json_prompt)
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise LLMProviderError(f"Gemini failed to return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "gemini"

    def test_connection(self) -> bool:
        """Test Gemini reachability with a small request."""

        try:
            self._model.generate_content("ping")
        except Exception as exc:  # pragma: no cover - network dependent
            raise LLMProviderError(f"Gemini connection test failed: {exc}") from exc
        return True
