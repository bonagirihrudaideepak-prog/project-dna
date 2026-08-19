import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import (
    ANALYSIS_MAX_BYTES,
    ANALYSIS_MAX_COMMITS,
    ANALYSIS_MAX_FILE_BYTES,
    ANALYSIS_MAX_FILES,
    ANALYSIS_TIMEOUT_SECONDS,
    CACHE_DEFAULT_TTL,
    CACHE_DNA_TTL,
    CACHE_LIST_TTL,
    CACHE_PROJECT_TTL,
    SESSION_TTL_SECONDS,
)


def _generate_strong_secret() -> str:
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True)

    env: str = "development"
    secret_key: str | None = None
    app_base_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://projectdna:projectdna@db:5432/projectdna"

    redis_url: str = "redis://redis:6379/0"
    # Cache TTL values (see config.constants)
    cache_default_ttl: int = CACHE_DEFAULT_TTL
    cache_dna_ttl: int = CACHE_DNA_TTL
    cache_project_ttl: int = CACHE_PROJECT_TTL
    cache_list_ttl: int = CACHE_LIST_TTL
    session_ttl_seconds: int = SESSION_TTL_SECONDS
    error_webhook_url: str = ""  # 7 days

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"
    github_token: str = ""

    # Analysis limits (see config.constants)
    analysis_max_files: int = ANALYSIS_MAX_FILES
    analysis_max_commits: int = ANALYSIS_MAX_COMMITS
    analysis_max_bytes: int = ANALYSIS_MAX_BYTES
    analysis_max_file_bytes: int = ANALYSIS_MAX_FILE_BYTES
    analysis_timeout_seconds: int = ANALYSIS_TIMEOUT_SECONDS
    analysis_tmp_root: str = "./tmp"

    fixture_root: str = "./fixtures"

    llm_provider: str = "none"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_provider_order: str = "auto"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 700
    llm_timeout_seconds: int = 60
    llm_ollama_base_url: str = "http://localhost:11434"
    llm_ollama_model: str = ""
    llm_ollama_token: str = ""
    llm_openrouter_api_key: str = ""
    llm_openrouter_model: str = "openai/gpt-4o-mini"
    llm_groq_api_key: str = ""
    llm_groq_model: str = "llama-3.3-70b-versatile"
    llm_gemini_api_key: str = ""
    llm_gemini_model: str = "gemini-2.0-flash"
    llm_nvidia_api_key: str = ""
    llm_nvidia_model: str = "meta/llama-3.3-70b-instruct"

    def llm_model_for(self, provider: str) -> str:
        explicit = getattr(self, f"llm_{provider}_model", "")
        if explicit:
            return explicit
        fallbacks = {
            "openrouter": "openai/gpt-4o-mini",
            "groq": "llama-3.3-70b-versatile",
            "gemini": "gemini-2.0-flash",
            "nvidia": "meta/llama-3.3-70b-instruct",
            "ollama": self.llm_ollama_model or "llama3.2",
        }
        return fallbacks.get(provider, self.llm_model)

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def validate_for_production(self) -> None:
        """Refuse unsafe config in production: weak secret, missing creds, or unsafe env."""
        if self.env != "production":
            return
        if not self.secret_key or self.secret_key == "change-me-in-production":
            raise RuntimeError("SECRET_KEY must be set to a strong random value in production")
        if len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 characters in production")
        if not self.github_client_id or not self.github_client_secret:
            raise RuntimeError("GitHub OAuth client_id and client_secret must be set in production")


settings = Settings()
if settings.env == "production":
    settings.validate_for_production()