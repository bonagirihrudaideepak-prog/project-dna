# CLAUDE.md

## What this is

Project DNA is a software archaeology & project intelligence platform. It analyzes
a repository's code, history, and tooling to produce an explainable 8-dimension
"DNA profile" (maintainability, testing maturity, documentation quality,
evolution health, delivery readiness, scalability readiness, technical
complexity, technical debt risk) plus a reconstructed decision/experiment/release
timeline. Monorepo: `apps/api` (FastAPI), `apps/web` (React), `fixtures`
(synthetic golden repos), `docs/`.

## Tech stack (versions that matter)

- **Backend:** Python ≥3.11 (dev uses 3.12), FastAPI ≥0.110, SQLAlchemy 2,
  Alembic, Pydantic v2 + pydantic-settings, psycopg 3, httpx, PyGithub, redis-py.
- **Frontend:** React 18.3, TypeScript 5.5, Vite 5, TanStack Query 5,
  react-router-dom 6, Recharts, Cytoscape.
- **DB/queue:** PostgreSQL 17; analysis jobs are a DB table claimed with
  `FOR UPDATE SKIP LOCKED` (lease-based). Cache: Redis (optional; degrades gracefully).
- **Lint:** Ruff 0.4+. **Tests:** pytest (+pytest-asyncio, `asyncio_mode=auto`), vitest.

## Commands

```bash
# API dev (from apps/api)
.venv\Scripts\python -m uvicorn app.main:app --port 8000
.venv\Scripts\python -m app.worker.main          # separate process, executes jobs

# API tests (needs DATABASE_URL set; integration tests use fixtures/)
.venv\Scripts\python -m pytest tests -q

# API lint
.venv\Scripts\python -m ruff check app tests

# DB migrations (from apps/api)
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m alembic revision --autogenerate -m "..."

# Seed fixture repos (from apps/api, FIXTURE_ROOT must be set)
.venv\Scripts\python scripts\seed.py

# Web dev / build / tests (from apps/web)
npm run dev
npm run build            # tsc -b && vite build  (must stay green)
npm run test             # vitest run
npx tsc --noEmit         # typecheck
```

Windows environment: set env vars with `$env:NAME="value"`, not `export`.

## Architecture — where things live and why

Clean/onion layering; **dependency direction is inward** — `interfaces` →
`application` → `domain` → `adapters`/`models`. Never import outward.

```
apps/api/app/
  interfaces/api/   # FastAPI routers (auth, projects, dna, archaeology, analysis)
  interfaces/       # deps.py (DI), schemas.py (Pydantic I/O contracts)
  application/      # use-case orchestration: analysis, similarity, exports, llm_service
  domain/analysis/  # pure domain logic:
    inspector.py        # untrusted-repo inspection (path traversal/zip-bomb guards)
    extractors/metrics.py   # raw metrics extraction
    scoring/            # dimensions, engine, normalize, pipeline, indicators/
    timeline/builder.py # decision/experiment/release timeline
    graph/builder.py    # evolution graph
  adapters/         # external I/O: db.py, cache.py, cache_service.py, github.py,
                    # llm/ (base, prompts, providers, router), metrics.py,
                    # security.py, sessions.py, rate_limit.py, errors.py
  models/           # SQLAlchemy ORM (identity, analysis, evolution, governance)
  config.py         # pydantic-settings Settings; constants live in config/constants.py
  worker/main.py    # job worker loop (lease claim + execute)
apps/web/src/
  hooks/            # TanStack Query hooks (useProjects, useDNA, useComparison, useTimeline, useJob)
  lib/api.ts        # typed API client; lib/types.ts shared contracts
  lib/components/   # primitives: Button, Card, ScoreCard
  components/       # ErrorBoundary, StateViews
  pages/            # route pages
```

## Code conventions (actually in the code)

- **Python:** Ruff `select = ["E4","E7","E9","F","I"]` only — no style rules;
  line-length 100; `target-version = "py311"`. Relative imports everywhere
  (`from .adapters import ...`, `from ..config import settings`).
- **`from __future__ import annotations`** at the top of every Python module.
- **Magic numbers** belong in `config/constants.py` (coverage thresholds, TTLs,
  limits, dimension order), then surfaced through `Settings`.
- **Error envelope:** all API errors return `{"error": {"code", "message", "retryable"}}`
  via handlers in `main.py`. Raise `DNAError` subclasses from `adapters/errors.py`
  (`NotFoundError`, `ValidationError`, `RateLimitedError`, `InsufficientCoverageError`, ...).
- **Scoring model (dna-core-1.0, ADR-001):** dimension score is
  `round(100·Σwᵢqᵢxᵢ / Σwᵢqᵢ)`; score is **withheld (null)** when `coverage < 0.35`,
  never reported as zero. `MIN_COMPARABLE_COVERAGE = 0.60` gates cross-snapshot
  comparison. New dimensions require updating `scoring/dimensions.py`,
  `scoring/pipeline.py` (or `scoring/indicators/`), and web `DIMENSION_LABELS`.
- **Web:** TanStack Query for all server state; data fetching lives in `hooks/`,
  never inline in pages; typed via `lib/types.ts` + `lib/api.ts`.
- **LLM output is never used for scoring** — only for narrative summaries, with
  deterministic template fallback.

## Hard rules (non-negotiables)

1. **Never change product behavior during refactors** — only quality/scalability/maintainability.
2. **Never weaken the inspector's untrusted-input guards** (path traversal, archive bombs, binary files).
3. **Never commit secrets** — `.env`, real keys, tokens. `SECRET_KEY` must be strong
   in production; OAuth is required in `ENV=production`.
4. **Respect coverage honesty** — never score a dimension with insufficient evidence; never turn null scores into zeros.
5. **Migrations are additive and reviewed** — follow Alembic; don't hand-edit applied migrations.
6. **Keep the app compiling/running after every step** when working on a task.

## Gotchas (week-1 landmines)

- **README layout is stale:** it still lists `app/analysis/`, `app/api/`,
  `app/github/`, `app/services/`. Real code lives under `domain/`, `interfaces/`,
  `application/`, `adapters/`. Don't trust the README tree; trust the actual files.
- **Relative-import depth matters:** `indicators/__init__.py` is one level deeper
  than `scoring/`, so its imports need one extra dot (`..engine`, `...inspector`).
  A wrong level throws `ModuleNotFoundError` only at runtime, not at parse time.
- **API and worker are separate processes** — both need `DATABASE_URL`. Job results
  appear only after the worker is running.
- **Redis may be absent in dev** — cache/`CacheService` must degrade to no-op, never crash.
- **Integration tests need a live DB** (`DATABASE_URL`); unit tests don't.
- **Windows:** PowerShell syntax (`$env:`, `.\venv\Scripts\python`); `&&` chains
  and `| head` do not work in this shell.
- **Fixture mode vs GitHub mode:** without OAuth env vars you can only analyze the
  three synthetic repos under `fixtures/`.