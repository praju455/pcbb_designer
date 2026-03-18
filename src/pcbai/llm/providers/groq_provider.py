"""Groq-backed LLM provider implementation."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError


class GroqLLMProvider(BaseLLMProvider):
    """Generate completions using the Groq chat completions API."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the Groq client from configuration."""

        settings = get_settings()
        if not settings.groq_api_key:
            raise LLMProviderError("GROQ_API_KEY is not configured. Add it to your .env file or shell.")

        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise LLMProviderError("The 'groq' package is not installed. Run 'pip install groq'.") from exc

        self._settings = settings
        self._console = console or Console(stderr=True)
        self._client = Groq(api_key=settings.groq_api_key)

    def _chat(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request to Groq."""

        with self._console.status(
            f"[bold cyan]Waiting for Groq ({self._settings.groq_model})[/bold cyan]", spinner="dots"
        ):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.groq_model,
                    messages=messages,
                    temperature=0.2,
                )
            except Exception as exc:  # pragma: no cover - network dependent
                raise LLMProviderError(f"Groq request failed: {exc}") from exc

        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise LLMProviderError("Groq returned an empty response.")
        return content.strip()

    def generate(self, prompt: str) -> str:
        """Generate plain text from a user prompt."""

        return self._chat([{"role": "user", "content": prompt}])

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON conforming to a schema, retrying on parse failures."""

        system_prompt = (
            "You are a precise JSON generator. Return only valid JSON that conforms to the provided schema. "
            "Do not use markdown fences or commentary."
        )
        schema_text = json.dumps(schema, indent=2)
        last_error: Exception | None = None

        for attempt in range(1, 4):
            raw = self._chat(
                [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nJSON schema:\n{schema_text}\n\nAttempt: {attempt}",
                    },
                ]
            )
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise LLMProviderError(f"Groq did not return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "groq"
