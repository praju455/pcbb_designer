"""Gemini provider implementation."""

from __future__ import annotations

import json
import re
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
            from google import genai
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise LLMProviderError("The google-genai package is not installed. Run pip install -e .") from exc

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._settings = settings
        self._console = console or Console(stderr=True)

    def _complete(self, prompt: str) -> str:
        """Execute a completion request."""

        with self._console.status(
            f"[bold cyan]Gemini verifying with {self._settings.gemini_model}[/bold cyan]",
            spinner="dots",
        ):
            try:
                response = self._client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=prompt,
                )
            except Exception as exc:  # pragma: no cover - network dependent
                raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        text = getattr(response, "text", "") or ""
        if not text.strip():
            raise LLMProviderError("Gemini returned an empty response.")
        return text.strip()

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract a JSON object from a raw model response."""

        cleaned = text.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.IGNORECASE | re.DOTALL)
        if fenced:
            cleaned = fenced.group(1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

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
                return self._extract_json(raw)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise LLMProviderError(f"Gemini failed to return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "gemini"

    def test_connection(self) -> bool:
        """Test Gemini reachability with a small request."""

        try:
            self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents="ping",
            )
        except Exception as exc:  # pragma: no cover - network dependent
            raise LLMProviderError(f"Gemini connection test failed: {exc}") from exc
        return True
