"""LLM provider abstractions.

Providers are OpenAI-compatible chat-completion clients (OpenRouter, Groq,
Gemini, NVIDIA all expose OpenAI-compatible endpoints; Ollama does too via
/v1/chat/completions). The router tries providers in configured order and
fails over to the next on error, so the app works even when one provider is
down, rate-limited, or missing a key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    """Raised when all configured providers fail."""


@dataclass
class LLMResult:
    provider: str
    model: str
    text: str


class LLMProvider(Protocol):
    name: str

    def chat(self, system: str, user: str) -> str:
        """Return the assistant text for the given messages."""
        ...
