# PRD: Trends & Alerts Dashboard

Feature: Trends & alerts dashboard for DNA profiles
Users: Engineering managers, tech leads, and platform teams who track a repo's health over time
Stack: React 18 + TS (Vite) frontend, FastAPI backend, PostgreSQL 17 (existing `repository_snapshots`, `dna_scores`, `analysis_jobs` tables), TanStack Query, Recharts

## 1. Problem statement + success metrics

Today DNA profiles are point-in-time: a user sees the latest snapshot's 8-dimension
scores with no sense of whether a repo is improving or decaying. Regressions in
maintainability or delivery readiness go unnoticed until someone re-runs analysis
and eyeballs two numbers side by side.

**Success metrics**
- % of analyzed projects with ≥2 snapshots that view the Trends view within 30 days (target > 40%).
- Median time from a dimension dropping below its alert threshold to a user seeing the alert (target < 24h).
- Alert click-through: ≥1 navigation from an alert to the dimension detail (target > 25% of alerts).
- No regression in existing DNA read paths (all current tests/build green).

## 2. User stories + acceptance criteria

- **US-1 Trends line chart** — As a tech lead, I want to see all 8 dimensions of a project over time so I can spot decay.
  - AC: GET `/projects/{id}/snapshots` (existing, ordered by `captured_at`), grouped dimension scores charted per snapshot.
  - AC: Null scores (coverage < 0.35) render as gaps, never as 0.
  - AC: Snapshots ordered by `captured_at` ascending; empty state when < 2 snapshots.
- **US-2 Alert rules** — As a platform engineer, I want to set per-project thresholds so I'm notified when a dimension regresses.
  - AC: Create/update/list/delete rules via new endpoints (`alerts` table).
  - AC: Rule = `dimension`, `operator` (lt/gt), `threshold`, `enabled`.
  - AC: Alerts computed when a snapshot completes (worker hook), not on read.
- **US-3 Alert inbox** — As a user, I want to see active/fired alerts for my projects.
  - AC: List alerts with dimension, snapshot, old vs new value, fired_at.
  - AC: Acknowledge (dismiss) alerts; dismissed alerts stop showing in the active list.
- **US-4 Comparison overlay** — As a user, I want the last two comparable snapshots highlighted on the chart.
  - AC: Only pairs where both sides have `coverage >= 0.60` for that dimension are marked comparable (reuse `MIN_COMPARABLE_COVERAGE`).

## 3. Scope

**v1 (ships)**
- Trends chart (US-1) with per-dimension series, gaps on null, hover tooltip.
- Alert rules CRUD (US-2) — one active rule per (project, dimension).
- Alert evaluation on snapshot completion (US-3 evaluation half).
- Alert list + acknowledge (US-3 list half).
- DB migration adding `alert_rules` and `alerts` tables.

**v2 (does not ship)**
- Cross-project benchmarks / percentiles.
- Email/Slack notification delivery.
- Alert rule groups (AND/OR conditions).
- Anomaly detection beyond fixed thresholds.
- Historical recompute of alerts for existing snapshots.

## 4. Data model changes

New tables (additive migration only — no changes to existing tables):

```
alert_rules
  id            uuid PK
  project_id    uuid FK -> projects(id) ON DELETE CASCADE, indexed
  dimension     varchar(40) not null
  operator      varchar(4)  not null          -- 'lt' | 'gt'
  threshold     int not null
  enabled       bool not null default true
  created_by    uuid FK -> users(id) nullable
  created_at, updated_at (TimestampMixin)
  UNIQUE (project_id, dimension)

alerts
  id            uuid PK
  rule_id       uuid FK -> alert_rules(id) ON DELETE CASCADE, indexed
  snapshot_id   uuid FK -> repository_snapshots(id) ON DELETE CASCADE, indexed
  dimension     varchar(40) not null          -- denormalized for fast list
  old_value     int nullable
  new_value     int nullable
  fired_at      timestamptz not null default now()
  acknowledged_at timestamptz nullable
  UNIQUE (rule_id, snapshot_id)
```

Both tables indexed on `project_id`/`rule_id` + `snapshot_id` to serve the trends
and inbox hot queries. `alerts.fired_at` and `acknowledged_at` support the inbox
sort/filter without scanning rules.

## 5. Edge cases + failure states

- **< 2 snapshots** → trends view shows empty state with "run a new analysis" CTA; no chart.
- **Null scores** → chart gap; alert evaluation **skips** dimensions with `coverage < 0.35` (do not alert on withheld scores).
- **Duplicate alerts** → `UNIQUE (rule_id, snapshot_id)` prevents double-fire on worker retry/re-claim.
- **Rule threshold crossed multiple times** → only the first crossing per snapshot fires an alert.
- **Snapshot re-analyzed (same id)** → alert row idempotent via unique constraint (upsert on conflict).
- **Deleted project / rule** → cascade removes dependent alerts.
- **Concurrent workers** → alert creation runs inside the snapshot-completion transaction; unique constraint is the backstop.
- **gte/lte operators** → v1 ships `lt`/`gt` only; `eq` rejected by schema validation.
- **Unavailable metric path** → if `dna_scores` read fails, the trends endpoint returns a 503-style `retryable` error envelope, never partial data.

## 6. Open questions

1. Alert **notification channel** for v1 — inbox-only, or also fire the existing `error_webhook_url` webhook on new alerts?
2. Should alert evaluation run in the **worker** immediately after scoring, or as a lazy post-analysis sweep?
3. Do users need **per-dimension drill-down** from an alert to the evidence breakdown in v1, or is the dimension name + old/new value enough?
4. **Multi-user projects** — do non-owner members see alerts, or owner-only for v1?
5. Threshold editing UX — inline on the dashboard, or a separate settings panel?