---
name: project-dna
description: >
  Work on the Project DNA monorepo (FastAPI backend + React web + fixtures).
  Use when making changes, running verification, debugging, adding features, or
  understanding this repo. Triggers: "work on project-dna", "run the checks",
  "verify the api", "run backend tests", "web build", "add a dimension", "which
  files", "how do I test this repo", "project DNA lint".
---

# Project DNA — Repo Workflow Skill

## What this is

A software archaeology & project intelligence platform. FastAPI backend
(`apps/api`), React/Vite web (`apps/web`), synthetic golden repos (`fixtures/`),
docs in `docs/`.

## Non-negotiables

1. Never change product behavior during refactors — quality/scale/maintainability only.
2. Never weaken the inspector's untrusted-input guards (path traversal, archive bombs, binary files).
3. Never commit secrets — `.env`, real keys. Production requires strong `SECRET_KEY` + OAuth.
4. Coverage honesty — never score a dimension with coverage < 0.35; never turn null scores into zeros.
5. Migrations are additive and reviewed — never hand-edit applied migration files; create new ones.
6. Keep the app compiling/running after every step.

## Before you touch code

1. Read `CLAUDE.md` at the repo root — it is the authoritative repo guide.
2. Locate the file(s) you'll touch and read the surrounding module for conventions.
3. For features, the spec in `docs/spec-*.md` (when present) is the source of truth;
   deviations require updating the spec first.
4. In this shell: Windows + PowerShell. No `&&` or `| head`. Env vars via `$env:NAME="..."`.
   `.venv\Scripts\python` (not `python`), and run backend commands from `apps/api`.

## Verify loop — run ALL of these after any change

### Backend (workdir: `apps/api`)
- Lint: `.venv\Scripts\python -m ruff check app tests migrations`
- Unit tests: `.venv\Scripts\python -m pytest tests/unit -q`
- Full suite (needs DB; skips fast without it): `.venv\Scripts\python -m pytest tests -q`
- Import smoke: `.venv\Scripts\python -c "import app.main, app.worker.main, app.mcp.server"`

### Web (workdir: `apps/web`)
- Typecheck: `npx tsc --noEmit`
- Unit: `npm run test`
- Build: `npm run build` (must stay green)
- E2E (needs dev server on 5173): `npm run test:e2e`

## Architecture map (what lives where)

Clean/onion layering; dependency direction is INWARD — `interfaces` →
`application` → `domain` → `adapters`/`models`. Never import outward.

- `apps/api/app/interfaces/api/` — FastAPI routers (auth, projects, dna, archaeology, analysis, alerts)
- `apps/api/app/interfaces/` — deps.py (DI), schemas.py (Pydantic I/O)
- `apps/api/app/application/` — use-case orchestration (analysis, similarity, exports, llm_service)
- `apps/api/app/domain/analysis/` — pure logic: inspector, extractors/metrics,
  scoring (dimensions, engine, normalize, pipeline, indicators/),
  timeline/builder, graph/builder
- `apps/api/app/domain/analysis/alerts.py` — alert rules; `evaluate_scores` fires
  on REGRESSION CROSSINGS (old >= threshold -> new < threshold for `lt`, etc.),
  not on being-past-threshold. No history -> no fire.
- `apps/api/app/adapters/` — db, cache, cache_service, github, llm/, metrics, security, sessions, rate_limit, errors
- `apps/api/app/models/` — SQLAlchemy ORM (identity, analysis, evolution, governance)
- `apps/api/app/config/constants.py` — magic numbers (coverage thresholds, TTLs, limits)
- `apps/api/app/worker/main.py` — job worker loop (lease claim + execute)
- `apps/api/app/mcp/server.py` — MCP 2.0 server (`MCPServer` + `@server.tool()` + `server.run(transport="stdio")`); relative imports need two dots (`from ..adapters.db import ...`)
- `apps/web/src/hooks/` — TanStack Query hooks; `lib/api.ts` + `lib/types.ts`
- `apps/web/src/lib/components/` — Button, Card, ScoreCard primitives
- `apps/web/src/pages/` — route pages

## Conventions that matter

- `from __future__ import annotations` at the top of every Python module.
- Relative imports everywhere; indicators/ is one level deeper so needs extra dot.
- Ruff select `["E4","E7","E9","F","I"]` only, line-length 100.
- Error envelope: `{"error": {"code", "message", "retryable"}}`; raise `DNAError`
  subclasses from `adapters/errors.py`.
- Scoring model: `round(100·Σwᵢqᵢxᵢ / Σwᵢqᵢ)`; withheld (null) when coverage < 0.35.
- New dimensions: update `scoring/dimensions.py`, `scoring/pipeline.py`, and web `DIMENSION_LABELS`.
- Web: all server state via TanStack Query in hooks/, typed via lib/types.ts + lib/api.ts.
- LLM output only for narrative summaries, never scoring.

## Security posture (do not regress)

- Every API write requires `current_user`; reads use `optional_user`.
- Cross-project access must go through `require_membership(db, project_id, user_id)`.
- No eval/exec/subprocess/pickle on untrusted input; SQL uses bound params.

## What to ask vs infer

- ASK: before migrations, before committing, before touching docs/, when a
  behavior change conflicts with a spec, when data fixtures are needed.
- INFER: file locations, verify-loop to run, conventions from surrounding code.

## Done means

- ruff clean, backend tests pass, `tsc --noEmit` clean, `npm run build` green,
  `npm run test` green (E2E when an API/DB is available or stubbed).
- No new secrets, no behavior changes unless spec-approved.
- Report the exact commands run and their results.