# Project DNA

A software archaeology & project intelligence platform. Analyze a repository's
code, history, and tooling to produce an explainable, 8-dimension "DNA profile"
of its maintainability, testing maturity, documentation quality, evolution
health, delivery readiness, scalability readiness, technical complexity, and
technical debt risk — plus a reconstructed timeline of decisions, experiments,
releases, and architectural changes.

**Status: production-hardened.** Security, observability, validation, error
handling, migration, and container hardening are in place; CI is provided.

## Stack

- **Frontend:** React 18 + TypeScript + Vite, TanStack Query, Recharts,
  Cytoscape (evolution graph).
- **Backend:** FastAPI + SQLAlchemy 2 + Alembic + Pydantic.
- **Queue:** Lightweight PostgreSQL-backed job table with lease-based claiming
  (`FOR UPDATE SKIP LOCKED`); a standalone worker process executes analyses.
- **DB:** PostgreSQL 17 (Docker).
- **Sources:** GitHub (real repos) or local synthetic fixtures (no credentials).

## Repository layout

```
project-dna/
  docker-compose.yml       # db + api + worker
  .env.example
  apps/
    api/
      app/                 # FastAPI application
        analysis/          # inspector, metrics, scoring, timeline, graph
        api/               # routers (auth, projects, dna, archaeology, analysis)
        github/            # GitHub adapter
        models/            # SQLAlchemy models
        services/          # analysis orchestration, similarity, exports
        worker/            # job worker
      migrations/          # Alembic
      tests/               # pytest (unit + integration)
      scripts/             # seed.py, smoke.py
    web/                   # React app
  fixtures/                # 3 synthetic golden repos
  docs/
    adr/                   # architecture decision records
    scoring-methodology/   # dimension & indicator definitions
    api/                   # API reference
```

## Quick start (local dev)

Prereqs: Docker (PostgreSQL), Python 3.12, Node 20+.

```bash
# 1. Start Postgres
docker compose up -d db

# 2. Backend
cd apps/api
uv venv --python 3.12 .venv            # or python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
$env:DATABASE_URL="postgresql+psycopg://projectdna:projectdna@localhost:5434/projectdna"
.\.venv\Scripts\python -m alembic upgrade head

# 3. Seed fixture projects (optional but recommended)
$env:FIXTURE_ROOT="C:\...\project-dna\fixtures"
.\.venv\Scripts\python scripts\seed.py

# 4. Run API + worker (two terminals)
$env:DATABASE_URL="..."; $env:FIXTURE_ROOT="..."; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000
$env:DATABASE_URL="..."; $env:FIXTURE_ROOT="..."; .\.venv\Scripts\python -m app.worker.main

# 5. Frontend
cd apps/web
npm install
npm run dev          # http://localhost:5173  (proxies /api -> :8000)
```

## Full stack via Docker

```bash
docker compose up --build
# api:  http://localhost:8000   worker: background   db: localhost:5434
```

## GitHub OAuth (optional)

Set `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and
`GITHUB_REDIRECT_URI` in `.env` or environment. Without OAuth, the app runs in
**fixture mode**: you can analyze the three synthetic repos immediately.

> In production (`ENV=production`) authentication is **required** and
> `SECRET_KEY` must be a strong random value. Fixture bypass only applies in
> development.

## Production deployment

The stack is containerized and hardened:

- **Non-root** runtime user in the API/worker image.
- **Migrations run automatically** at container start (`alembic upgrade head`).
- **Healthchecks** on the API and DB; `restart: unless-stopped` policies.
- **Secrets via environment**, never baked into the image or committed.
- The DB port is **not** exposed publicly by default.

```bash
# 1. Configure secrets (see .env.example). At minimum:
#    ENV=production, SECRET_KEY=<strong random>, POSTGRES_PASSWORD=<strong>,
#    and the LLM/GitHub keys you use.
cp .env.example .env

# 2. Build and start db + api + worker
docker compose up -d --build

# 3. Verify readiness
curl http://localhost:8000/api/health/ready
```

Frontend: build with `npm run build` in `apps/web` and serve the `dist/`
directory behind a TLS-terminating reverse proxy that proxies `/api` to the
API container. Configure `ALLOWED_ORIGINS` and `APP_BASE_URL` to match the
public origin, and set cookie flags (`SESSION_COOKIE_SECURE=true`) when
serving over HTTPS.

## CI

`.github/workflows/ci.yml` runs backend pytest, frontend vitest, the frontend
production build, and a Docker image build on every push/PR.

## Testing

```bash
# backend (needs DATABASE_URL env var; integration tests use fixture files)
cd apps/api
.\.venv\Scripts\python -m pytest tests -q

# frontend
cd apps/web
npm run test
```

## Docs

- [Architecture decisions](docs/adr/ADR-001-dna-core-model.md)
- [Scoring methodology](docs/scoring-methodology/dimensions.md)
- [API reference](docs/api/reference.md)

## License

Private / internal MVP. Repository content is treated as untrusted input
(inspector guards path traversal, archive bombs, and binary files).