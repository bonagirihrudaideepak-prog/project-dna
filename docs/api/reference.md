# API Reference

Base URL: `http://localhost:8000`. The web app proxies `/api/*` from
`http://localhost:5173` to `http://localhost:8000`.

- Routers are mounted under `/api/v1`.
- `GET /api/health`, `GET /api/methodology`, and `GET /api/fixtures` are
  unauthenticated and live at the root.
- Responses are `application/json`. Errors use `{"error_code": "DB_ERROR"}` for
  database failures or `{"error": {"code": "...", "message": "...", "retryable": true}}`
  for application errors.

## Health, methodology, fixtures

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | `{"status":"ok","app":"project-dna","version":"0.1.0"}` |
| GET | `/api/methodology` | Active model version, dimension definitions, normalization thresholds |
| GET | `/api/fixtures` | Available fixtures and whether each is imported |

## Auth

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/auth/github/start` | Redirect to GitHub OAuth authorize |
| GET | `/api/v1/auth/github/callback?code=...` | OAuth callback, sets session cookie |
| GET | `/api/v1/auth/me` | Current user (null if logged out) |
| POST | `/api/v1/auth/logout` | End session |

Without OAuth configured the app runs in **fixture mode** (analyze fixtures, no
login required).

## Projects (with pagination)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/github/repositories` | Repos available for import (GitHub mode), `?per_page=30` |
| POST | `/api/v1/projects/import` | Import a repo or fixture; body `{"full_name":"owner/repo"}` |
| GET | `/api/v1/projects` | List projects with pagination: `?page=1&per_page=50` |
| GET | `/api/v1/projects/{project_id}` | Project detail |
| DELETE | `/api/v1/projects/{project_id}` | Delete a project |
| POST | `/api/v1/projects/{project_id}/analyses` | Queue an analysis; returns an `AnalysisJob` |
| GET | `/api/v1/analysis-jobs/{job_id}` | Job state, progress, phase, error |
| POST | `/api/v1/analysis-jobs/{job_id}/cancel` | Cancel a pending job |
| GET | `/api/v1/projects/{project_id}/snapshots` | Snapshots for a project |
| GET | `/api/v1/snapshots/{snapshot_id}` | Snapshot detail |

Job states: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`. A standalone worker
claims leased jobs and executes them; the web app polls the job.

DNA

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/snapshots/{snapshot_id}/dna` | 8 scored dimensions with indicator detail |
| GET | `/api/v1/snapshots/{snapshot_id}/dna/{dimension}` | Single dimension |

Dimension payload:
```json
{
  "dimension": "maintainability",
  "score": 64,
  "coverage": 0.63,
  "confidence": "low",
  "direction": "higher_is_better",
  "model_version": "dna-core-1.0",
  "indicators": [{"key":"hotspot_dispersion","raw_value":0.4,"normalized_value":0.7,"quality":0.8,"evidence_ids":[]}],
  "limitations": []
}
```
`score` is `null` (withheld) when coverage < 0.35. `technical_debt_risk` direction
is `lower_is_better`; all other quality dimensions are `higher_is_better`.

## Timeline

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/snapshots/{snapshot_id}/timeline` | Chronological events (newest first) |
| GET | `/api/v1/timeline-events/{event_id}` | Single event detail |
| GET | `/api/v1/snapshots/{snapshot_id}/hotspots` | Churn/fix hotspots |
| GET | `/api/v1/snapshots/{snapshot_id}/metrics` | Raw computed metrics |

Event types: `release`, `pr`, `issue`, `commit_cluster`, `dependency_change`,
`decision`, `experiment`. Each carries `provenance` and `confidence`.

## Archaeology (decisions, experiments)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/projects/{project_id}/decisions` | Decisions for a project |
| POST | `/api/v1/projects/{project_id}/decisions` | Create a decision |
| GET | `/api/v1/decisions/{decision_id}` | Decision detail |
| POST | `/api/v1/decisions/{decision_id}/outcome-reviews` | Add an outcome review |
| GET | `/api/v1/projects/{project_id}/experiments` | Failed-experiments archive |
| POST | `/api/v1/projects/{project_id}/experiments` | Record a failed experiment |

## Compare, summaries, exports

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/comparisons` | Body `{"snapshot_a":"id","snapshot_b":"id"}`; similarity or null when <2 comparable dims |
| GET | `/api/v1/snapshots/{snapshot_id}/graph` | Evolution graph (bounded); query `?focus=<node>&depth=1` |
| POST | `/api/v1/snapshots/{snapshot_id}/summaries` | Generate a summary (deterministic unless LLM configured) |
| GET | `/api/v1/summaries/{summary_id}` | Fetch a generated summary |
| POST | `/api/v1/snapshots/{snapshot_id}/exports?fmt=json|html` | Export the snapshot DNA report |
| GET | `/api/v1/exports` | List exports |

## Methodology

`GET /api/methodology` returns the active model version, dimension definitions,
and normalization thresholds — the source of truth used by the UI's
Methodology page.