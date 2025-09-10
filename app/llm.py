"""LLM client implementations for the study app.

This module provides a small abstraction layer around language models.  It
ships with a ``MockLLM`` used in tests and a ``GeminiLLM`` implementation that
calls Google's Gemini models.  A ``build_llm`` helper instantiates the desired
client based on application settings.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol, TYPE_CHECKING


class LLM(Protocol):
    """Protocol that all LLM clients must satisfy."""

    def score(self, prompt: str) -> dict:
        """Return a parsed JSON dict from the model for the given prompt."""


@dataclass
class MockLLM:
    """A simple mock LLM returning deterministic results."""

    def score(self, prompt: str) -> dict:
        # The mock simply returns a fixed structure
        return {
            "score": 100,
            "feedback": "Great job!",
            "flashcards": [],
        }


@dataclass
class GeminiLLM:
    """LLM client for Google's Gemini models."""

    api_key: str
    model_name: str

    def __post_init__(self) -> None:
        try:  # Lazy import so tests can run without the dependency installed
            import google.generativeai as genai
        except Exception as exc:  # pragma: no cover - exercised only when missing
            raise RuntimeError("google-generativeai package not installed") from exc

        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    def score(self, prompt: str) -> dict:
        """Send the prompt to Gemini and parse the JSON response."""

        response = self._model.generate_content(prompt)
        text = getattr(response, "text", None)
        if not text:  # Fallback if the client returns candidates/parts structure
            candidate = getattr(response, "candidates", [None])[0]
            if candidate is not None:
                parts = getattr(candidate.content, "parts", [])
                if parts:
                    text = getattr(parts[0], "text", None)
        if not text:
            raise RuntimeError("No text returned from Gemini")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini response was not valid JSON") from exc


if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from .config import Settings


def build_llm(settings: "Settings" | None = None) -> LLM:
    """Factory to create an LLM client based on configured provider."""

    if settings is None:
        from .config import settings as cfg
        settings = cfg

    provider = settings.llm_provider.lower()
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini API key not configured")
        return GeminiLLM(api_key=settings.gemini_api_key, model_name=settings.model_name)

    # Default to the mock implementation for tests or local development
    return MockLLM()

