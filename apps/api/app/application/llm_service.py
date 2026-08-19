"""LLM summarization service with automatic provider failover and deterministic fallback.

The service tries configured LLM providers in order until one succeeds. If all
providers fail (or LLM is disabled), it returns a grounded deterministic summary
built from the available evidence — never used for scoring, only for UI display.
"""

from __future__ import annotations

from typing import Any

from ..adapters.llm.base import LLMError
from ..adapters.llm.prompts import PROMPT_VERSION, build_messages, validate_output
from ..adapters.llm.router import LLMResult
from ..config import settings

DEFAULT_MODEL = "openai/gpt-4o-mini"


class LLMService:
    """Encapsulates LLM calls with failover and deterministic fallback."""

    def __init__(self, provider_order: str | None = None):
        self._provider_order = provider_order

    def _order(self) -> list[str]:
        raw = (self._provider_order or settings.llm_provider_order or "").strip()
        if not raw or raw.lower() in ("none", "auto"):
            return ["openrouter", "groq", "gemini", "nvidia", "ollama"]
        return [p.strip() for p in raw.split(",") if p.strip()]

    def _model_for(self, provider: str) -> str:
        explicit = getattr(settings, f"llm_{provider}_model", "")
        if explicit:
            return explicit
        fallbacks = {
            "openrouter": "openai/gpt-4o-mini",
            "groq": "llama-3.3-70b-versatile",
            "gemini": "gemini-2.0-flash",
            "nvidia": "meta/llama-3.3-70b-instruct",
            "ollama": settings.llm_ollama_model or "llama3.2",
        }
        return fallbacks.get(provider, settings.llm_model)

    def _is_configured(self, provider: str) -> bool:
        if provider == "ollama":
            return True
        return bool(getattr(settings, f"llm_{provider}_api_key", "") or "")

    def chat(self, system: str, user: str, timeout: float = 60.0) -> LLMResult:
        """Try each configured provider; return the first success or raise LLMError."""
        order = self._order()
        last_error: Exception | None = None

        for provider in order:
            if provider not in settings.llm_provider_order and provider not in (
                "openrouter",
                "groq",
                "gemini",
                "nvidia",
                "ollama",
            ):
                last_error = Exception(f"Unknown provider '{provider}'")
                continue
            if not self._is_configured(provider):
                last_error = Exception(f"Provider '{provider}' is not configured (missing key)")
                continue
            try:
                model = self._model_for(provider)
                text = self._chat_provider(provider, model, system, user, timeout=timeout)
                return LLMResult(provider=provider, model=model, text=text)
            except Exception as exc:  # noqa: BLE001 - fail over on any error
                last_error = exc

        raise LLMError(f"All LLM providers failed: {last_error}")

    def _chat_provider(
        self, provider: str, model: str, system: str, user: str, timeout: float
    ) -> str:
        """Delegate to the concrete provider chat function."""
        from ..adapters.llm import providers

        return providers.chat(provider, model, system, user, timeout=timeout)

    def summarize_snapshot(
        self,
        project_name: str,
        snapshot_sha: str,
        timeline_text: str,
        dna_text: str,
        decisions_text: str,
        experiments_text: str,
    ) -> dict[str, Any]:
        """Generate a grounded summary for a snapshot.

        Tries LLM providers with automatic failover. If all fail, returns
        a deterministic template built from the evidence.
        """
        system_msg, user_msg = build_messages(
            project_name, snapshot_sha, timeline_text, dna_text, decisions_text, experiments_text
        )

        try:
            result = self.chat(system_msg, user_msg, timeout=settings.llm_timeout_seconds)
            parsed, status, reason = validate_output(result.text)
            if status == "ok":
                _persist_llm_run(
                    snapshot_id="",
                    purpose="summary",
                    provider=result.provider,
                    model=result.model,
                    system=system_msg,
                    user=user_msg,
                    output=parsed,
                    status="ok",
                )
                return {
                    "summary": parsed["summary"],
                    "claims": [{"text": h, "evidence_ids": []} for h in parsed["highlights"][:5]],
                    "uncertainties": parsed["uncertainties"],
                    "validation_status": "ok",
                    "ai_assisted": True,
                    "provider": result.provider,
                    "model": result.model,
                    "prompt_version": PROMPT_VERSION,
                }
        except Exception:  # noqa: BLE001 - fail over to deterministic
            pass

        # Deterministic fallback
        return {
            "summary": self._deterministic_summary(timeline_text, dna_text),
            "claims": [],
            "uncertainties": ["Summary generated from evidence without LLM assistance."],
            "validation_status": "ok",
            "ai_assisted": False,
            "provider": "deterministic",
            "model": "n/a",
            "prompt_version": PROMPT_VERSION,
        }

    def _deterministic_summary(self, timeline_text: str, dna_text: str) -> str:
        """Build a deterministic fallback summary from available evidence."""
        lines = []
        if dna_text.strip():
            lines.append("DNA profile: " + dna_text.strip())
        if timeline_text.strip():
            lines.append("Timeline: " + timeline_text.strip())
        return " | ".join(lines) if lines else "No summary available."


def _persist_llm_run(
    db,
    snapshot_id: str,
    purpose: str,
    provider: str,
    model: str,
    system: str,
    user: str,
    output: dict,
    status: str,
) -> None:
    from ..models import LLMRun

    input_ids = [line for line in user.splitlines() if line.startswith("- ")][:50]
    run = LLMRun(
        snapshot_id=snapshot_id,
        purpose=purpose,
        provider=provider,
        model=model,
        prompt_version=PROMPT_VERSION,
        input_evidence_ids=input_ids,
        output_json=output,
        validation_status=status,
    )
    db.add(run)
    db.commit()