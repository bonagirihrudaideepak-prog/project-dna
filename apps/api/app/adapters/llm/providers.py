"""Concrete LLM providers.

All remote providers are spoken to over OpenAI-compatible chat completions
endpoints. Ollama is detected specially so local inference (no API key) works
out of the box.
"""

from __future__ import annotations

import httpx

from ...config import settings
from ...config.constants import LLM_DEFAULT_MODELS, LLM_OLLAMA_DEFAULT_MODEL
from .base import LLMError

DEFAULT_MODELS: dict[str, str] = {
    **LLM_DEFAULT_MODELS,
    "ollama": settings.llm_ollama_model or LLM_OLLAMA_DEFAULT_MODEL,
}

ENDPOINTS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "ollama": settings.llm_ollama_base_url,
}


def _api_key(provider: str) -> str:
    return getattr(settings, f"llm_{provider}_api_key", "") or ""


def is_configured(provider: str) -> bool:
    """A provider is usable if it has a key (or is a local Ollama)."""
    if provider == "ollama":
        return True
    return bool(_api_key(provider))


def chat(provider: str, model: str, system: str, user: str, timeout: float = 60.0) -> str:
    base = ENDPOINTS.get(provider)
    if not base:
        raise LLMError(f"Unknown provider: {provider}")
    url = f"{base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if provider == "ollama":
        # Ollama requires no auth header; some installs are behind a token
        if settings.llm_ollama_token:
            headers["Authorization"] = f"Bearer {settings.llm_ollama_token}"
    else:
        key = _api_key(provider)
        if not key:
            raise LLMError(f"Provider '{provider}' has no API key configured")
        headers["Authorization"] = f"Bearer {key}"
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://project-dna.local"
        headers["X-Title"] = "Project DNA"

    payload: dict = {
        "model": model or DEFAULT_MODELS.get(provider, "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    if provider in ("gemini", "nvidia"):
        payload["max_completion_tokens"] = payload.pop("max_tokens")
    if provider == "groq":
        payload.pop("max_tokens", None)  # Groq reads max_completion_tokens

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise LLMError(f"{provider} request failed: {exc}") from exc
    except ValueError as exc:
        raise LLMError(f"{provider} returned non-JSON: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"{provider} response missing choices: {data!r:.200}") from exc
