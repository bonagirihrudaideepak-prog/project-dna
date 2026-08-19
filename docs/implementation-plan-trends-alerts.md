# Implementation Plan — Trends & Alerts Dashboard

Numbered build sequence for `docs/spec-trends-alerts.md` and
`docs/prd-trends-alerts.md`. Every step leaves the app compiling and running.

Legend: **S** small (<30 min) · **M** medium · **L** large.

---

## Step 1 — Alert data models + relationship **[M]** ✅

- Files: `apps/api/app/models/analysis.py`, `apps/api/app/models/identity.py`,
  `apps/api/app/models/__init__.py`.
- Adds `AlertRule` and `Alert` ORM models (unique `(project_id, dimension)` and
  `(rule_id, snapshot_id)`), and `Project.alert_rules` relationship.
- Verify: `import app.main` compiles; `app/models/__init__.py` exports the new models.

## Step 2 — Migration 0003_alerts **[S]** ✅

- File: `apps/api/migrations/versions/0003_alerts.py`.
- Additive: creates `alert_rules` + `alerts` with CHECK constraints, FKs, indexes.
- Rollback: `alembic downgrade 0002` (drops both tables, nothing else touched).
- Verify: `alembic upgrade head` when a DB is available; `alembic downgrade 0002`
  round-trips.

## Step 3 — Pydantic schemas **[S]** ✅

- File: `apps/api/app/interfaces/schemas.py`.
- `AlertRuleIn` (dimension, `operator` pattern `^(lt|gt)$`, `threshold` 0–100),
  `AlertRuleOut`, `AlertOut`, `TrendPoint`.
- Verify: unit schema tests / `import app.main`.

## Step 4 — Pure alert logic + unit tests **[M]** ✅

- File: `apps/api/app/domain/analysis/alerts.py`.
- Pure functions: `evaluate_scores`, `previous_score` (first non-null earlier score),
  no I/O, deterministic. Coverage < 0.35 → skip (honesty rule).
- File: `apps/api/tests/unit/test_alerts.py` — 8 tests (operator directions, threshold
  boundaries, null-skip, previous-score lookup, idempotency target).
- Verify: `pytest tests/unit -q` all green.

## Step 5 — Wire evaluation into the worker **[M]** ✅

- File: `apps/api/app/worker/main.py`.
- `_evaluate_and_store_alerts(snapshot)` called on the worker's success path in
  `worker_once()`; idempotent via `(rule_id, snapshot_id)` unique.
- Verify: `import app.worker.main`; unit tests.

## Step 6 — Latent import-bug cleanup (prerequisite) **[M]** ✅

- Files: `app/config/__init__.py` (was `config.py`, collision with `config/`),
  `adapters/errors.py`, `adapters/github.py`, `application/llm_service.py`,
  `main.py`, `domain/analysis/scoring/indicators/__init__.py`,
  `interfaces/api/analysis.py` (dead fallback removed, `llm="none"` path fixed).
- No behavior change; the app could not import before this step.
- Verify: `import app.main`, `import app.worker.main`, `ruff check app`, full unit suite.

## Step 7 — API endpoints **[M]** ✅

- File: `apps/api/app/interfaces/api/alerts.py`; router registered in `app/main.py`.
- `GET/POST/PATCH/DELETE /projects/{id}/alerts`, `GET /projects/{id}/trends`,
  `GET /alerts`, `POST /alerts/{id}/acknowledge`.
- Writes require `current_user`; reads `optional_user`; all gated by
  `require_membership`.
- Verify: `import app.main`; ruff; integration tests (skipped without DB).

## Step 8 — Web: types, API client, hooks **[M]** ✅

- Files: `apps/web/src/lib/types.ts`, `lib/api.ts`, `hooks/useTrends.ts`,
  `hooks/useAlerts.ts`; `useDNA.ts` deduped (comparison/timeline hooks live in their
  own files).
- Verify: `npx tsc --noEmit` clean.

## Step 9 — TrendsPage + routing **[M]** ✅

- Files: `apps/web/src/pages/TrendsPage.tsx` (chart + rules + alerts),
  `apps/web/src/App.tsx` (route `/projects/:id/trends`),
  `pages/ProjectDetailPage.tsx` (card link).
- Verify: `npm run build` green; `npm run test` passes.

## Step 10 — Tests **[S]** ✅

- Files: `apps/api/tests/integration/test_alerts.py` (DB-gated, skips fast via
  `connect_timeout=2` probe).
- Verify: full `pytest tests -q` and web vitest.

## Step 11 — Security audit of the new surface **[S]** ✅

- IDOR on snapshot-by-ID reads fixed in `analysis.py`/`dna.py`/`archaeology.py`;
  unauthenticated writes fixed in `archaeology.py`/`projects.py`/`alerts.py`.
- Verify: ruff, unit suite, `import app.main`.

## Step 12 — Dead code sweep **[S]** ✅

- Removed stub `GET /exports`; fixed stale README layout tree.
- Verify: build + full test suite.

---

## Risk register

| Risk | Mitigation | Rollback |
| ---- | ---------- | -------- |
| Migration conflicts on existing DBs | Additive only; downgrade `0002` | `alembic downgrade 0002` |
| Duplicate alerts on re-run | `UNIQUE (rule_id, snapshot_id)` | delete alert rows |
| Alert noise with withheld scores | Coverage gate + null skip in logic | delete rules |
| Breaking trend chart with 1 snapshot | "Not enough data" state, `hasTrends` gate | revert TrendsPage |

## Verification summary (final state)

- Backend: 57 passed, 1 skipped; ruff clean; `import app.main` + `app.worker.main` OK.
- Web: `tsc --noEmit` clean; `npm run build` green; vitest passes.
- Integration: DB-dependent tests skip when Postgres is absent (fast-fail probe).
- Known gap: no live DB in this environment, so migration apply + integration run
  remain unverified locally.