"""Gemini-backed LLM provider implementation."""

from __future__ import annotations

import json
from typing import Any

import requests
from rich.console import Console

from pcbai.core.config import get_settings
from pcbai.llm.provider import BaseLLMProvider, LLMProviderError


class GeminiLLMProvider(BaseLLMProvider):
    """Generate completions using the Gemini REST API."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the provider from configuration."""

        self._settings = get_settings()
        if not self._settings.gemini_api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured. Add it to your .env file or shell.")
        self._console = console or Console(stderr=True)
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _post(self, model: str, prompt: str, system: str | None = None) -> dict[str, Any]:
        """Call a Gemini content generation endpoint."""

        payload: dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        with self._console.status(
            f"[bold cyan]Waiting for Gemini ({model})[/bold cyan]", spinner="dots"
        ):
            try:
                response = requests.post(
                    f"{self._base_url}/models/{model}:generateContent",
                    params={"key": self._settings.gemini_api_key},
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise LLMProviderError(f"Gemini request failed: {exc}") from exc
        return response.json()

    def generate(self, prompt: str) -> str:
        """Generate plain text from a user prompt."""

        payload = self._post(self._settings.gemini_model, prompt)
        candidates = payload.get("candidates", [])
        try:
            return candidates[0]["content"]["parts"][0]["text"].strip()
        except (IndexError, KeyError, TypeError) as exc:
            raise LLMProviderError("Gemini returned an unexpected response payload.") from exc

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON conforming to a schema, retrying on parse failures."""

        system_prompt = (
            "Return only valid JSON matching the provided schema. "
            "Do not wrap the response in markdown or explanation."
        )
        schema_text = json.dumps(schema, indent=2)
        last_error: Exception | None = None
        for attempt in range(1, 4):
            raw = self.generate(f"{prompt}\n\nJSON schema:\n{schema_text}\n\nAttempt: {attempt}")
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = exc
        raise LLMProviderError(f"Gemini did not return valid JSON after 3 attempts: {last_error}")

    def get_provider_name(self) -> str:
        """Return the provider name."""

        return "gemini"

    def list_available_models(self) -> list[str]:
        """List Gemini models accessible with the configured key."""

        try:
            response = requests.get(
                f"{self._base_url}/models",
                params={"key": self._settings.gemini_api_key},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LLMProviderError(f"Unable to list Gemini models: {exc}") from exc
        models = response.json().get("models", [])
        return sorted(model.get("name", "").split("/")[-1] for model in models if model.get("name"))
