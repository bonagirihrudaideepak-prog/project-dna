"""Failover router: try configured providers in order until one answers."""

from __future__ import annotations

from ..config import settings
from . import providers
from .base import LLMError, LLMResult

FALLBACK_ORDER = ["openrouter", "groq", "gemini", "nvidia", "ollama"]
_TIMEOUT_SECONDS = 60.0


def configured_provider_order() -> list[str]:
    raw = (settings.llm_provider_order or "").strip()
    if not raw or raw.lower() in ("none", "auto"):
        return FALLBACK_ORDER
    return [p.strip() for p in raw.split(",") if p.strip()]


def router_chat(system: str, user: str, timeout: float = _TIMEOUT_SECONDS) -> LLMResult:
    """Try each configured provider; return the first success or raise LLMError."""
    order = configured_provider_order()
    last_error: Exception | None = None
    for provider in order:
        if provider not in providers.ENDPOINTS:
            last_error = LLMError(f"Unknown provider '{provider}' in llm_provider_order")
            continue
        if not providers.is_configured(provider):
            last_error = LLMError(f"Provider '{provider}' is not configured (missing key)")
            continue
        try:
            model = settings.llm_model_for(provider)
            text = providers.chat(provider, model, system, user, timeout=timeout)
            return LLMResult(provider=provider, model=model, text=text)
        except httpx.HTTPStatusError as exc:  # noqa: BLE001 - fail over on HTTP errors
            status = exc.response.status_code if exc.response else 0
            # Do not fail over on 4xx auth/client errors — those will never succeed
            # without config changes; instead surface them immediately.
            if 400 <= status < 500:
                raise LLMError(f"Provider '{provider}' client error: {exc}") from exc
            last_error = exc
        except httpx.HTTPError as exc:  # noqa: BLE001 - fail over on network errors
            last_error = exc
        except Exception as exc:  # noqa: BLE001 - fail on unexpected errors
            last_error = exc
    raise LLMError(f"All LLM providers failed: {last_error}")
