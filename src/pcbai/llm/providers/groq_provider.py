"""Groq provider implementation."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError


class GroqLLMProvider(BaseLLMProvider):
    """LLM provider backed by Groq chat completions."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the Groq SDK client."""

        settings = get_settings()
        if not settings.groq_api_key:
            raise LLMProviderError("GROQ_API_KEY is not set. Add it to .env before using Groq.")
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise LLMProviderError("The groq package is not installed. Run pip install -e .") from exc

        self._settings = settings
        self._console = console or Console(stderr=True)
        self._client = Groq(api_key=settings.groq_api_key)

    def _complete(self, messages: list[dict[str, str]]) -> str:
        """Execute a chat completion request."""

        with self._console.status(
            f"[bold cyan]Groq generating with {self._settings.groq_model}[/bold cyan]",
            spinner="dots",
        ):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.groq_model,
                    messages=messages,
                    temperature=0.2,
                )
            except Exception as exc:  # pragma: no cover - network dependent
                raise LLMProviderError(f"Groq request failed: {exc}") from exc

        if not response.choices or not response.choices[0].message.content:
            raise LLMProviderError("Groq returned an empty response.")
        return response.choices[0].message.content.strip()

    def generate(self, prompt: str) -> str:
        """Generate plain text."""

        return self._complete([{"role": "user", "content": prompt}])

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate schema-shaped JSON, retrying on parse failures."""

        system_prompt = (
            "Return only valid JSON matching the provided schema. "
            "Do not include markdown fences, explanations, or surrounding text."
        )
        schema_text = json.dumps(schema, indent=2)
        last_error: Exception | None = None

        for attempt in range(1, 4):
            raw = self._complete(
                [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nSchema:\n{schema_text}\n\nAttempt {attempt} of 3.",
                    },
                ]
            )
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise LLMProviderError(f"Groq failed to return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "groq"

    def test_connection(self) -> bool:
        """Test that Groq can complete a minimal request."""

        try:
            self._client.chat.completions.create(
                model=self._settings.groq_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
        except Exception as exc:  # pragma: no cover - network dependent
            raise LLMProviderError(f"Groq connection test failed: {exc}") from exc
        return True
