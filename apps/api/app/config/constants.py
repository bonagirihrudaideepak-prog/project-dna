"""Project DNA constants and configuration defaults."""

from __future__ import annotations

# Coverage thresholds (per ADR-001)
COVERAGE_INSUFFICIENT: float = 0.35
COVERAGE_LOW: float = 0.60
COVERAGE_MODERATE: float = 0.80
COVERAGE_HIGH: float = 1.01

# Comparable coverage for cross-snapshot comparison
MIN_COMPARABLE_COVERAGE: float = 0.60

# Analysis limits
ANALYSIS_MAX_FILES: int = 10_000
ANALYSIS_MAX_COMMITS: int = 2_000
ANALYSIS_MAX_BYTES: int = 209_715_200  # 200 MiB
ANALYSIS_MAX_FILE_BYTES: int = 524_288  # 512 KiB
ANALYSIS_TIMEOUT_SECONDS: int = 3_600  # 1 hour

# Default TTL values (seconds)
CACHE_DEFAULT_TTL: int = 300       # 5 minutes
CACHE_DNA_TTL: int = 900           # 15 minutes
CACHE_PROJECT_TTL: int = 60        # 1 minute
CACHE_LIST_TTL: int = 30           # 30 seconds

# Session
SESSION_TTL_SECONDS: int = 604_800  # 7 days

# GitHub
GITHUB_ARCHIVE_DOWNLOAD_TIMEOUT: int = 120  # seconds

# LLM
LLM_TIMEOUT_SECONDS: int = 60
LLM_TEMPERATURE: float = 0.2
LLM_MAX_TOKENS: int = 700

# Per-provider default models when no llm_<provider>_model is configured.
# Ollama's default is dynamic (settings.llm_ollama_model) and handled by consumers.
LLM_DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "openai/gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "nvidia": "meta/llama-3.3-70b-instruct",
}
LLM_OLLAMA_DEFAULT_MODEL: str = "llama3.2"

# Prometheus histogram buckets
HISTOGRAM_BUCKETS: tuple[float, ...] = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# Dimension order (per ADR-001)
DIMENSION_ORDER: list[str] = [
    "technical_complexity",
    "maintainability",
    "testing_maturity",
    "documentation_quality",
    "evolution_health",
    "delivery_readiness",
    "scalability_readiness",
    "technical_debt_risk",
]

# List-endpoint guardrails: generous ceilings so unbounded growth cannot OOM a
# request; normal projects are far below these.
TRENDS_MAX_SNAPSHOTS: int = 200
SNAPSHOTS_MAX_LIST: int = 200
TIMELINE_MAX_EVENTS: int = 500
PROJECT_REFERENCES_MAX: int = 500
ALERTS_INBOX_MAX: int = 200

# Analysis job states (kept in one place; SQL literals must match)
JOB_STATE_QUEUED: str = "QUEUED"
JOB_STATE_RUNNING: str = "RUNNING"
JOB_STATE_RETRY: str = "RETRY"
JOB_STATE_COMPLETED: str = "COMPLETED"
JOB_STATE_FAILED: str = "FAILED"
JOB_STATE_CANCELLED: str = "CANCELLED"

# Confidence label thresholds (ascending)
COVERAGE_LABEL_THRESHOLDS: list[tuple[float, str]] = [
    (0.35, "insufficient"),
    (0.60, "low"),
    (0.80, "moderate"),
    (1.01, "high"),
]