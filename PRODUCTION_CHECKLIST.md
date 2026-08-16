# Project DNA — Architecture

## High-Level Architecture

The application follows **Clean Architecture** with three primary layers:

### 1. Domain Layer (Core Business Logic)
- **Models**: SQLAlchemy 2.0 ORM models with declarative base, UUID primary keys, timestamp tracking
- **Scoring Engine**: Evidence-weighted DNA scoring with 8 dimensions, each composed of named indicators with fixed weights
- **Analysis Pipeline**: Converts inspection data + artifacts + file changes into indicator inputs, then applies scoring engine
- **Services**: Analysis orchestration, similarity comparison, export generation

### 2. Interface Adapters Layer (API & Gateways)
- **FastAPI Routers**: HTTP endpoints mounted under `/api/v1`
- **GitHub Adapter**: REST API client for GitHub data fetching with rate limiting and error handling
- **LLM Router**: Failover provider router trying configured providers in order with automatic fallback
- **Workers**: PostgreSQL-backed job processor with lease-based claiming (`FOR UPDATE SKIP LOCKED`)

### 3. Infrastructure Layer
- **PostgreSQL 17**: Primary data store with JSONB for flexible metadata, UUID extensions
- **Alembic**: Database migration management (versions 0001 initial + 605daba23479 FK indexes)
- **Docker**: Containerized API, worker, and DB services via docker-compose
- **Postfix-style Logging**: Structured JSON lines with correlation IDs (request IDs)

### Data Flow

```
HTTP Request
    → FastAPI Middleware (request ID, CORS, error handlers)
    → Router (auth validation, input parsing)
    → Service Layer (analysis orchestration, scoring, exports)
    → Repository Layer (SQLAlchemy ORM → PostgreSQL)
    → Response (JSON, error envelopes, headers)
```

### Authentication Flow

1. User initiates GitHub OAuth at `/api/v1/auth/github/start`
2. Rate-limited IP check + state token generation
3. User redirected to GitHub authorize URL
4. GitHub callback exchanges code for access token
5. Token encrypted via Fernet (derived from SECRET_KEY) and persisted
6. Session cookie set (HttpOnly, SameSite=Lax, Secure in production)
7. Subsequent requests: cookie decoded → `current_user` dependency injects user

### Authorization Flow

- `optional_user` dependency: in production, enforces auth via `current_user`
- In development: fixture projects readable without authentication
- `require_membership`: checks ProjectMembership for access control
- All API endpoints validate user permissions before data access

### Event Flow (Analysis Pipeline)

1. Job claimed by worker with lease (`JOB_LEASE_SECONDS=600`)
2. Source data fetched (GitHub API or FixtureSource)
3. Repository archive inspected (path traversal guards, binary detection, size limits)
4. Metrics computed from inspected files (structural breadth, dependency breadth, churn, etc.)
5. Scoring engine applies dimension indicators with evidence-quality weighting
6. Timeline events built from artifacts, file changes, decisions, experiments
7. Evolution graph constructed from events, decisions, experiments
8. Results persisted transactionally; job marked COMPLETED or FAILED
9. Lease refreshed on every progress update (dead man's switch monitoring)

### Cache Strategy

- **Response headers**: `X-Request-ID` for correlation
- **No server-side caching** required for core data (database is source of truth)
- **Client-side**: TanStack React Query with `staleTime: 30s` for API queries
- **No Redis** in current deployment; could be added for session caching if needed

## Folder Structure

```
project-dna/
├── docker-compose.yml          # db + api + worker services
├── .env.example               # Environment configuration template
├── .github/                   # CI/CD workflows
├── apps/
│   ├── api/                   # FastAPI backend
│   │   ├── app/               # Application code
│   │   │   ├── __init__.py    # Package init
│   │   │   ├── config.py      # Pydantic settings (production-hardened)
│   │   │   ├── db.py          # SQLAlchemy engine + session management
│   │   │   ├── models/        # SQLAlchemy models (base + 7 entity modules)
│   │   │   ├── schemas.py     # Pydantic response models
│   │   │   ├── security.py    # Token encryption/decryption, JWT
│   │   │   ├── deps.py        # FastAPI dependencies (auth, user resolution)
│   │   │   ├── main.py        # FastAPI app entrypoint
│   │   │   ├── api/           # Router modules (auth, projects, dna, archaeology, analysis)
│   │   │   ├── services/      # Analysis orchestration, exports, similarity
│   │   │   ├── worker/        # Job worker main entrypoint
│   │   │   ├── llm/           # LLM provider base, router, prompts, providers
│   │   │   ├── analysis/      # Inspector, scoring pipeline, timeline, graph
│   │   │   │   ├── extractors/ # Metrics computation (structural, dependency, etc.)
│   │   │   │   ├── scoring/   # Dimensions, engine, pipeline
│   │   │   │   ├── inspector.py # Safe archive inspection
│   │   │   │   ├── timeline/  # Rule-based timeline builder
│   │   │   │   └── graph/     # Evolution graph builder
│   │   │   └── migrations/    # Alembic migration versions
│   │   ├── tests/             # pytest unit + integration tests
│   │   │   ├── unit/          # Unit tests (scoring, normalize, similarity, inspector)
│   │   │   ├── integration/   # Fixture-based integration tests
│   │   │   └── conftest.py    # Test environment configuration
│   │   ├── scripts/           # Seed and smoke scripts
│   │   ├── Dockerfile         # Production-hardened Docker image
│   │   ├── pyproject.toml     # Package configuration + dependencies
│   │   └── .env               # Local secrets (gitignored)
│   └── web/                   # React + Vite frontend
│       ├── src/
│       │   ├── App.tsx        # Root component with routing + TanStack Query
│       │   ├── main.tsx       # React root render
│       │   ├── index.css      # Global styles with CSS variables
│       │   ├── lib/
│       │   │   ├── api.ts     # Typed API client
│       │   │   ├── types.ts   # TypeScript interfaces for all domain objects
│       │   │   └── format.ts  # UI formatting helpers (confidence colors, labels)
│       │   ├── hooks/
│       │   │   └── useJob.ts  # Job polling hook
│       │   ├── components/
│       │   │   ├── ErrorBoundary.tsx  # React error boundary
│       │   │   └── StateViews.tsx     # Loading/error/empty states
│       │   ├── features/      # Feature modules (auth, dna, projects, timeline, etc.)
│       │   │   └── pages/     # Page components (Projects, DNA, Compare, etc.)
│       │   └── lib/           # Utility modules
│       ├── package.json       # Dependencies (React 18, TanQuery, Recharts, Cytoscape)
│       ├── tsconfig.json      # TypeScript configuration
│       └── vite.config.ts   # Vite build config
├── fixtures/                  # 3 synthetic golden repos (manifest.json + repo data)
│   ├── synthetic-minimal-repo/
│   ├── synthetic-mature-repo/
│   ├── synthetic-small-repo/
│   ├── synthetic-evolution-repo/
│   └── synthetic-small-repo/
├── docs/
│   ├── adr/                   # Architecture Decision Records
│   │   └── ADR-001-dna-core-model.md
│   ├── scoring-methodology/ # Dimension & indicator definitions
│   │   └── dimensions.md
│   └── api/                   # API reference (reference.md)
├── packages/
│   └── contracts/             # Type/shared-contracts (currently empty)
├── scripts/                   # Utility scripts (seed.py, smoke.py)
└── README.md                  # Project overview + quick start + deployment guide
```

## Database Schema

The database uses PostgreSQL 17 with SQLAlchemy 2.0 ORM. Schema is defined through
ORM models with Alembic migration management.

### Entity-Relationship Overview

```
users               github_connections    projects
│                   │                     │
│                   │FK: user_id        │
│                   │                     │FK: owner
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
│                   │                     │FK: project_id
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
│                   │                     │FK: project_id
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
project_memberships   repository_snapshots   decisions
│                   │                   │
│FK: project_id     │FK: project_id     │FK: project_id
│FK: user_id        │                   │FK: author_user_id
│                   │                   │
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
repository_snapshots  analysis_jobs         experiments
│                   │FK: snapshot_id    │
│FK: project_id     │state/phase/prog   │FK: project_id
│commit_sha         │attempts/lease     │start_at/evaluated_at
│status             │error_detail       │decision/result
│captured_at        │                   │archived
│                   │                   │
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
snapshots            dna_scores            timeline_events
│                   │FK: snapshot_id    │FK: project_id
│snapshot_id        │dimension/score      │FK: snapshot_id
│commit_sha         │coverage/confidence │type/title/summary
│analyzer_version   │explanation_json    │occurred_at/end_at
│score_model_version│model_version       │provenance/confidence
│status/warnings    │                   │metadata_json
│                   │                   │
├───────────────────┼───────────────────────┼──────────────────────┘
│                   │                     │
artifacts            metric_values         graph_nodes
│FK: snapshot_id    │FK: snapshot_id    │FK: project_id
│type/provider_id   │key/normalized_value │entity_type/entity_id
│title/source_url   │evidence_json       │metadata_json
│bytes/lines        │                   │
│content_hash       │                   │
│is_generated       │                   │
│                   │                   │
event_artifacts      graph_edges           graph_edges
│FK: event_id       │FK: source_node_id ││FK: target_node_id
│FK: artifact_id    │FK: target_node_id │edge_type/provenance
│relation           │confidence         │evidence_json
│                   │                   │
artifacts            score_evidence      exports
│FK: snapshot_id    │FK: score_id       │FK: project_id
│type/provider_id   │FK: metric_value_id│FK: snapshot_id
│title/source_url   │quality/contribution│status/format
│content_hash       │                   │expires_at
│                   │                   │
file_changes         file_records
│commit_artifact_id │FK: snapshot_id    │FK: snapshot_id
│file_path          │path/extension     │
│additions/deletions│language/category  │
│change_type        │content_hash       │
│occurred_at        │is_generated       │
│                   │                   │
file_records        metric_values
│FK: snapshot_id    │key/normalized_value│
│path/extension     │evidence_json      │
│bytes/lines        │                   │
│category           │                   │
│content_hash       │                   │
│is_generated       │                   │
```

### Key Indexes

- `users.github_user_id` (unique)
- `users.login` (unique)
- `github_connections.user_id` + `github_connections.revoked_at`
- `project_memberships.project_id` + `project_memberships.user_id`
- `repository_snapshots.project_id` + `repository_snapshots.status`
- `dna_scores.snapshot_id` + `dna_scores.dimension`
- `metric_values.snapshot_id` + `metric_values.key`
- `timeline_events.project_id` + `timeline_events.snapshot_id`
- `graph_nodes.project_id` + `graph_nodes.snapshot_id`
- `decision_alternatives.decision_id`
- `experiment_links.experiment_id`

## API Design

### Response Envelopes

All API responses follow consistent patterns:

**Success responses**: Return the requested resource or data array
**Error responses**: `{"error": {"code": "ERROR_CODE", "message": "Human-readable message", "retryable": true/false}}`
**List responses**: `{"items": [...], "total": N, "page": 1, "per_page": 20, "total_pages": 2}`

### Standard Error Codes

| Code | Meaning | Retryable |
|---|---|---|
| `VALIDATION_ERROR` | Input validation failed | No |
| `AUTHENTICATION_ERROR` | Missing/invalid session | No |
| `AUTHORIZATION_ERROR` | User lacks project membership | No |
| `NOT_FOUND` | Resource doesn't exist | No |
| `CONFLICT` | Resource already exists or constraint violation | No |
| `DB_ERROR` | Database operation failed | Yes |
| `RATE_LIMITED` | Too many requests (OAuth only) | Yes |
| `GITHUB_RATE_LIMITED` | GitHub API rate limit exceeded | Yes |
| `LLM_ERROR` | All LLM providers failed | No (surface immediately) |
| `DEAD_MAN_SWITCH` | Job lease stale (worker) | N/A |

### Pagination

List endpoints support `?page=N&per_page=N` query parameters.
Response envelope includes `total`, `page`, `per_page`, `total_pages`.

### Key Endpoints

| Category | Endpoint | Method | Auth |
|---|---|---|---|
| Health | `/api/health` | GET | Public |
| Methodology | `/api/methodology` | GET | Public |
| Fixtures | `/api/fixtures` | GET | Public |
| Auth Start | `/api/v1/auth/github/start` | GET | Public (rate-limited) |
| Auth Callback | `/api/v1/auth/github/callback` | GET | OAuth |
| Me | `/api/v1/auth/me` | GET | Session |
| Projects List | `/api/v1/projects` | GET | Optional |
| Project Import | `/api/v1/projects/import` | POST | Optional |
| Queue Analysis | `/api/v1/projects/{id}/analyses` | POST | Optional |
| Job Status | `/api/v1/analysis-jobs/{id}` | GET | Optional |
| DNA Scores | `/api/v1/snapshots/{id}/dna` | GET | Optional |
| Timeline | `/api/v1/snapshots/{id}/timeline` | GET | Optional |
| Compare | `/api/v1/comparisons` | POST | Optional |
| Export | `/api/v1/snapshots/{id}/exports` | POST | Optional |

## Implementation

### Production-Ready Code Conventions

- **Type safety**: Python `from __future__ import annotations`, TypeScript strict types
- **Validation**: Pydantic models for all request/response schemas
- **Error handling**: FastAPI exception handlers for `SQLAlchemyError` and generic `Exception`
- **Logging**: Structured JSON lines with request ID correlation
- **Retry logic**: Exponential backoff not yet implemented but framework present
- **Pagination**: Cursor/offset-based via query parameters
- **Filtering**: Query parameter-based on list endpoints
- **Sorting**: By created_at desc as default on list endpoints

### Key Implementation Details

**Database Migrations**: Alembic is the source of truth for schema evolution. `init_db()` uses
`Base.metadata.create_all(bind=engine, checkfirst=True)` as a safety net for local development,
but production relies on `alembic upgrade head` at container startup (defined in docker-compose).

**Worker Lease Management**: Jobs claimed with `SELECT ... FOR UPDATE SKIP LOCKED`. Lease duration
`JOB_LEASE_SECONDS=600` (10 minutes). Dead man's switch triggers if lease not refreshed within
`DEAD_MAN_SWITCH_SECONDS=300` (5 minutes). Jobs that exceed `analysis_timeout_seconds` are failed.

**LLM Failover**: Router tries providers in configured order. Rate limit errors (5xx) trigger failover.
4xx client errors (missing keys) surface immediately since failover won't help. "none" provider order
disables LLM and returns deterministic fallback.

**Scoring Engine**: Evidence-weighted formula:
```
score(d) = round(100 * sum(w*q*x) / sum(w*q))
coverage(d) = sum(w*q) / sum(w)
confidence = f(coverage)  # insufficient < low < moderate < high
```
Score withheld when coverage < 0.35. Technical debt risk inverts scores (lower_is_better).

**Security by Design**:
- Repository text treated as untrusted input
- Path traversal guards in archive inspection (`safe_join`)
- Archive bomb limits (200k entries, 1GB expansion)
- Binary file rejection
- Fernet-encrypted OAuth tokens (never plaintext persisted)
- JWT session tokens with HS256
- Cookie-only authentication (no query param leakage)
- Rate limiting on OAuth start endpoint (20 req/60s per IP)

## Security Audit

### OWASP Top 10 Coverage

| Risk | Status | Notes |
|---|---|---|
| A01:2021 — Broken Access Control | **Fixed** | Role-based access via ProjectMembership checks; fixture projects world-readable in dev only |
| A02:2021 — Cryptographic Failures | **Fixed** | Fernet encryption for OAuth tokens; JWT with HS256; secret key enforced >= 32 chars in prod |
| A03:2021 — Injection | **Fixed** | Path traversal guards (`safe_join`), archive bomb limits, binary detection |
| A04:2021 — Insecure Design | **Fixed** | Threat modeling done; untrusted input guards throughout |
| A05:2021 — Security Misconfiguration | **Fixed** | Secret key validation at startup; env var required in production |
| A06:2021 — Vulnerable Components | **Monitoring** | Dependencies monitored via pip; no known vulnerabilities at audit |
| A07:2021 — Identification & Authentication Failures | **Fixed** | Session cookies with HttpOnly/SameSite/Secure; JWT validation; rate-limited OAuth |
| A08:2021 — Software & Data Failures | **Fixed** | Archive safety limits, binary detection, error redacting |
| A09:2021 — Security Logging & Monitoring | **Good** | Structured JSON logging with request IDs; health checks on API/DB |
| A10:2021 — Server-Side Request Forgery | **Good** | No external URL validation from user input; GitHub API calls only |

### Attack Scenarios & Fixes

1. **Session Cookie Hijacking**
   - *Scenario*: attacker steals HttpOnly session cookie via XSS
   - *Fix*: `secure` flag on cookies in production (HTTPS only); `SameSite=Lax`; no sensitive data in URLs

2. **OAuth State Interception**
   - *Scenario*: attacker guesses/replays OAuth state parameter
   - *Fix*: 256-bit state token with TTL (10 minutes); in-memory store with LRU eviction (max 10k entries)

3. **SQL Injection**
   - *Scenario*: malicious input in project IDs or search queries
   - *Fix*: `parse_id()` validates UUID format before DB queries; SQLAlchemy ORM parameterization

4. **Archive Bomb/Path Traversal**
   - *Scenario*: malformed zip archive causes DoS or file exfiltration
   - *Fix*: `MAX_ENTRIES=200_000`, `MAX_EXPANDED_BYTES=1_000_000_000`, `safe_join()` with resolve() comparison

5. **LLM Prompt Injection**
   - *Scenario*: malicious repository content influences LLM output
   - *Fix*: LLM only summarizes evidence we already hold; output validated structurally; never used for scoring

### Secrets Management

- `SECRET_KEY`: Must be set in production (>= 32 chars, random); raised as RuntimeError if missing
- `GITHUB_CLIENT_ID/SECRET`: OAuth credentials; required for GitHub mode
- `POSTGRES_PASSWORD`: Docker Compose; not baked into image
- API keys (LLM providers): Via `.env`; never committed (gitignored)
- No secrets baked into Docker images; all via environment at runtime

## Performance Analysis

### Big-O Complexity Summary

| Component | Complexity | Notes |
|---|---|---|
| Scoring pipeline | O(n + m) | n = files, m = artifacts; metrics are linear in inspected data |
| Similarity comparison | O(d) | d = 8 dimensions (constant); negligible |
| Graph building | O(e + v) | e = edges, v = nodes; linear in events/decisions/experiments |
| Timeline building | O((a + f) log (a + f)) | a = artifacts, f = file changes; sort-driven |
| Indicator computation | O(f) | f = files; each metric scans file list once |
| Database queries | O(1) with proper indexes | All list endpoints use pagination + batch loading |

### Database Bottlenecks & Optimizations

1. **N+1 Query Prevention**: `list_projects` uses batch `func.max()` + single query for latest snapshots
2. **Index Coverage**: All foreign key columns indexed; critical query paths verified
3. **Connection Pooling**: `pool_pre_ping=True` handles stale connections gracefully
4. **Query Batching**: `selectinload` used for relationship loading in archaeology endpoints

### Rendering Performance

- **Frontend**: TanStack React Query with `staleTime: 30s`; Recharts for DNA radar/bar charts
- **Code splitting**: Route-based lazy loading via `lazy()` + `Suspense`
- **Bundle size**: ~2MB initial load (React 18 + TanStack + Recharts + Cytoscape)
- **No virtualization needed** for current data volumes (typically < 200 timeline events)

### Memory Management

- **Worker**: Job lease prevents unbounded memory retention; dead man's switch reclaims stale jobs
- **Analysis**: Archive data held in temp directory; cleaned up after inspection
- **LLM**: Responses held in memory only during summary generation; then persisted to DB as LLMRun

## Testing Strategy

### Test Pyramid

```
           +------------------+
           |  End-to-End      |
           |  (fixture-based) |
           +------------------+
           |  Integration     |
           |  (pipeline runs) |
           +------------------+
           |    Unit          |
           |  (engine, metrics)|
           +------------------+
```

### Unit Tests

- **Scoring engine**: `test_scoring.py` — coverage/confidence rules, dimension directions, single-dimension scoring
- **Normalization**: `test_normalize.py` — clamp01, linear, capped_ratio, log_scale, inverted, inverse_weighted
- **Similarity**: `test_similarity.py` — model compatibility, weight inversion, coverage exclusion
- **Inspector**: `test_inspector.py` — path traversal guards, binary detection, file categorization

### Integration Tests

- **Fixture pipeline**: `test_fixtures.py` — runs full analysis pipeline against synthetic repos
- Verifies all 8 dimensions produced, evidence handling, score withholding, confidence labels
- Tests minimal fixture (most dimensions withheld), mature fixture (real scores), evolution fixture (rework detection)

### Test Configuration

- `conftest.py`: Sets `DATABASE_URL`, `FIXTURE_ROOT`, `ENV=test`, `SECRET_KEY=test-secret-development-only`
- Integration tests use fixture repos (no GitHub credentials needed)
- All tests run via `cd apps/api && .venv\Scripts\pytest tests -q`

### Coverage Goals

- **Unit test target**: 80%+ on scoring engine, normalization, similarity
- **Integration test target**: Full pipeline exercise against all 3+ fixture repos
- **Edge case target**: Missing evidence, zero coverage, boundary coverage thresholds (0.35, 0.60)

### Continuous Integration

`.github/workflows/ci.yml` runs:
- Backend pytest unit + integration tests
- Frontend vitest unit tests
- Frontend production build
- Docker image build on every push/PR

## DevOps Plan

### CI/CD Pipeline

`.github/workflows/ci.yml` executes on every push/PR:

1. **Backend**: `pytest` unit + integration tests (requires Docker + PostgreSQL)
2. **Frontend**: `vitest` unit tests + `npm run build` production build
3. **Docker**: Image build for API and worker services
4. **Lint**: `ruff` Python linting + TypeScript checking
5. **Publish**: Docker images to container registry on main branch

### Environment Configuration

| Environment | Key Variables |
|---|---|
| Development | `ENV=development`, weak `SECRET_KEY`, GitHub OAuth optional |
| Staging | `ENV=staging`, strong `SECRET_KEY`, GitHub OAuth required |
| Production | `ENV=production`, `SECRET_KEY` validated >= 32 chars, GitHub OAuth required, LLM keys optional |

### Secrets Management

- **Never commit** `.env` files or API keys
- Use Docker Compose `env_file` to load from `.env` at runtime
- Production secrets injected via orchestration platform (K8s Secrets, Azure Key Vault, etc.)
- `.env.example` provides the schema; users copy to `.env` and fill values

### Docker Deployment

```bash
# 1. Copy and configure env
cp .env.example .env
# Edit .env with production values

# 2. Start stack
docker compose up -d --build

# 3. Verify
curl http://localhost:8000/api/health/ready

# 4. Check logs
docker compose logs -f api
docker compose logs -f worker
```

### Health Checks

- **API**: `GET /api/health` and `GET /api/health/ready` (verifies DB connectivity)
- **DB**: `pg_isready` (via Docker healthcheck)
- **Worker**: Implicit via job claiming loop; no explicit endpoint

### Rollback Strategy

1. `docker compose down` stops all services
2. `docker compose up -d` restarts previous stack (data persists in pgdata volume)
3. Alembic migrations are versioned; `downgrade` available if needed
4. Rollback window: 30 minutes post-deployment; after that, manual schema recovery

### Monitoring & Logging

- **Structured logs**: JSON lines via `logging_utils.JsonFormatter`
- **Correlation IDs**: `X-Request-ID` header on all API responses
- **Health endpoints**: `/api/health`, `/api/health/ready`
- **Error envelopes**: Consistent `{"error": {"code", "message", "retryable"}}` format
- **No PII in logs**: Repository content treated as untrusted; no secrets logged

### Alerting

- Dashboard alerts for: API health check failures, DB connection failures, worker crash loops, high error rates (>5% of requests), LLM provider outages

## Future Improvements

### Phase 1 — Q3 2026
- [ ] Add Redis for session caching and rate limiting
- [ ] Implement per-project API rate limits
- [ ] Add WebSocket endpoints for real-time job progress
- [ ] Enhance LLM provider with tool calling support
- [ ] Add API versioning (v1/v2)

### Phase 2 — Q4 2026
- [ ] Migrate from SQLite-based fixture testing to full GitHub integration test matrix
- [ ] Add performance benchmark suite
- [ ] Implement read replica for PostgreSQL
- [ ] Add comprehensive OpenAPI/Swagger documentation
- [ ] Add SSO integration (SAML/OIDC) beyond GitHub

### Phase 3 — 2027
- [ ] Graph database integration (Neo4j) for large evolution graphs
- [ ] Real-time collaboration features (conflict-free decisions)
- [ ] Cost-optimized LMR (Large Model Routing) with provider switching
- [ ] Multi-tenant isolation with tenant_id on all entities
- [ ] CLI tool for local analysis without web UI

### Technical Debt Paydown
- [ ] Replace in-memory state store with Redis-backed state for distributed worker support
- [ ] Add database connection pooling metrics and auto-scaling
- [ ] Implement comprehensive integration test matrix across all fixture combinations
- [ ] Add property-based testing for scoring engine invariants

## Risks

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PostgreSQL data loss | Low | High | Regular backups via `pg_dump`, pgdata volume with restart policy |
| Worker job starvation | Medium | Medium | Dead man's switch reclamation; configurable lease duration |
| LLM cost overruns | Medium | Medium | Provider failover; "none" mode disables LLM entirely; token usage tracking |
| OAuth rate limiting | High | Low | IP bucket (20/60s); state store with TTL; graceful degradation to fixture mode |
| Schema migration downtime | Low | Medium | Alembic online migrations; `if_not_exists` on index creation |

### Security Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fernet key compromise | Low | High | Rotate `SECRET_KEY`; key derivation from strong secret; monitor for unauthorized access |
| XSS in frontend | Medium | Medium | Content Security Policy headers; sanitize all user-rendered content |
| JWT token forgery | Low | High | HS256 with validated >= 32-char secret; token expiry (7 days); refresh cycle |
| Archive-based attacks | Low | High | Entry count limit, byte expansion limit, path traversal guards, binary detection |

### Scalability Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Single-worker bottleneck | Medium | Medium | Add worker replica scale; job lease supports concurrent claiming |
| PostgreSQL connection exhaustion | Low | High | `pool_pre_ping`, connection limits, health check circuit breaker |
| Memory growth in long-running analysis | Medium | Medium | Temp directory cleanup; archive size limits; progress-based GC |

## Production Checklist

### Pre-Deployment

- [ ] `SECRET_KEY` set to >= 32 random characters (generated via `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] `ENV=production` in environment
- [ ] `POSTGRES_PASSWORD` set to strong value (not `projectdna`)
- [ ] `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` configured if GitHub mode needed
- [ ] LLM API keys configured optionally (or `LLM_PROVIDER_ORDER=none` for deterministic mode)
- [ ] `ALLOWED_ORIGINS` set to public domain (not localhost)
- [ ] `APP_BASE_URL` set to public URL
- [ ] Database backed up before `docker compose up`
- [ ] Alembic migration at head: `alembic upgrade head` verified

### Post-Deployment

- [ ] `curl http://localhost:8000/api/health` returns `{"status":"ok",...}`
- [ ] `curl http://localhost:8000/api/health/ready` returns `{"status":"ok","database":"ok"}`
- [ ] `curl http://localhost:8000/api/methodology` returns dimension definitions
- [ ] Fixture mode works: `curl http://localhost:8000/api/fixtures` returns 3 repos
- [ ] Session cookie set on auth flow; `httpOnly: true`, `secure: true` (HTTPS)
- [ ] No `SECRET_KEY == "change-me-in-production"` in any config
- [ ] Ruff lint passes: `ruff check .`
- [ ] Production build passes: `cd apps/web && npm run build`
- [ ] All unit tests pass: `cd apps/api && .venv\Scripts\pytest tests -q`
- [ ] Integration tests pass: `cd apps/api && .venv\Scripts\pytest tests/integration -q`
- [ ] Worker process starts and claims jobs: `python -m app.worker.main`
- [ ] Health check endpoint responsive within 2 seconds
- [ ] No warnings on `docker compose up -d --build`

### Ongoing Operations

- [ ] Monitor health endpoints every 60 seconds
- [ ] Review logs for error patterns daily
- [ ] Rotate `SECRET_KEY` every 90 days
- [ ] Track LLM usage and costs weekly
- [ ] Backup database weekly via `pg_dump`
- [ ] Update dependency packages monthly
- [ ] Review OAuth state store size monthly (max 10k entries)