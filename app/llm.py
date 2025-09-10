"""Minimal LLM client abstractions."""

from __future__ import annotations

from dataclasses import dataclass


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
