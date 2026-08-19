# Spec — Trends & Alerts Dashboard

Source of truth for the trends and alerts feature. Implemented behavior; any future
change must update this spec first.

Companion docs: `docs/prd-trends-alerts.md` (why), `docs/implementation-plan-trends-alerts.md`
(how it was built).

---

## 1. Behavior

### 1.1 Trends line chart

**Given** a project with ≥ 2 completed snapshots and DNS scores,
**when** `GET /projects/{project_id}/trends` is called,
**then** it returns one point per snapshot, ordered oldest → newest, with a score per
dimension.

- Each point has `snapshot_id`, `captured_at`, `created_at`, and `scores` (map of
  dimension → score).
- **Coverage honesty:** a dimension whose score was withheld (coverage < 0.35) is
  rendered as `null`, never as 0. The chart renders these as gaps.
- **Given** a project with zero snapshots, **then** `[]` is returned.

### 1.2 Alert rules (CRUD)

- **List:** `GET /projects/{project_id}/alerts` → all rules for the project.
- **Create:** `POST /projects/{project_id}/alerts`:
  - `dimension` must be one of the 8 DNA dimensions, else `422`.
  - `operator` must be `lt` or `gt`, `threshold` in `[0, 100]`, else `422`.
  - One rule per dimension: a second rule on the same dimension → `409`.
  - Requires auth + project membership.
- **Update:** `PATCH /projects/{project_id}/alerts/{rule_id}`:
  - Replaces `dimension`, `operator`, `threshold`.
  - Rule must exist and belong to the project, else `404`.
- **Delete:** `DELETE /projects/{project_id}/alerts/{rule_id}` → `{"ok": true}`.
  - Rule must exist and belong to the project, else `404`.

### 1.3 Alert evaluation (worker-side)

**Given** an analysis job completes for snapshot N,
**when** the worker finalizes it,
**then** for every enabled rule on the project:
- Let `new = score(snapshot N, dimension)`.
- Let `old = score(previous snapshot, dimension)`, found by scanning earlier snapshots
  for the first non-null score (matching the rule's dimension).
- If `new` or `old` is null → skip (coverage honesty).
- If `operator == "lt"` and `old ≥ threshold` and `new < threshold` → fire
  (crossed below the threshold).
- If `operator == "gt"` and `old ≤ threshold` and `new > threshold` → fire
  (crossed above the threshold).
- A dimension already on the alert side that stays there is NOT a crossing and
  does not re-fire; a baseline is required to detect a regression.
- Firing is **idempotent**: at most one alert per `(rule, snapshot)`.
- `fired_at` is set at evaluation time.

### 1.4 Alert inbox

- **List:** `GET /alerts?acknowledged=false` (default) → unacknowledged alerts,
  newest first, max 200.
  - With `acknowledged=true`, acknowledged alerts are included.
  - Dev: includes alerts for fixture projects (world-readable).
  - Prod: only alerts on projects the caller is a member of; anonymous → empty.
- **Acknowledge:** `POST /alerts/{alert_id}/acknowledge` → sets `acknowledged_at`,
  returns `{"ok": true}`. Requires auth + membership on the owning project.
  - Already acknowledged → no-op, still `{"ok": true}`.

---

## 2. API contract

### 2.1 TrendPoint

```json
{
  "snapshot_id": "uuid",
  "captured_at": "iso8601|null",
  "created_at": "iso8601|null",
  "scores": { "maintainability": 72, "testing_maturity": null }
}
```

### 2.2 AlertRuleIn / AlertRuleOut

```json
// In
{ "dimension": "maintainability", "operator": "lt", "threshold": 40 }
// Out (201 on create)
{ "id": "uuid", "project_id": "uuid", "dimension": "maintainability",
  "operator": "lt", "threshold": 40, "enabled": true }
```

### 2.3 AlertOut

```json
{ "id": "uuid", "rule_id": "uuid", "snapshot_id": "uuid",
  "dimension": "maintainability", "old_value": 55, "new_value": 38,
  "fired_at": "iso8601", "acknowledged_at": null }
```

### 2.4 Error shape

All errors use the global envelope `{"error": {"code", "message", "retryable"}}`.

| Code   | HTTP | When |
| ------ | ---- | ---- |
| 401    | 401  | No/invalid session (writes) |
| 403    | 403  | Not a member of the project |
| 404    | 404  | Project/rule/alert not found, or rule from another project |
| 409    | 409  | Rule already exists for that dimension |
| 422    | 422  | Bad dimension, operator, or threshold; malformed UUID |

---

## 3. Data model

Migration `0003_alerts`:

```
alert_rules
  id            UUID PK
  project_id    UUID FK -> projects.id  (NOT NULL)
  dimension     text NOT NULL
  operator      text NOT NULL CHECK (operator IN ('lt','gt'))
  threshold     int  NOT NULL CHECK (threshold BETWEEN 0 AND 100)
  enabled       bool NOT NULL DEFAULT true
  created_by    UUID FK -> users.id
  created_at    timestamptz NOT NULL DEFAULT now()
  UNIQUE (project_id, dimension)

alerts
  id               UUID PK
  rule_id          UUID FK -> alert_rules.id  (NOT NULL, ON DELETE CASCADE)
  snapshot_id      UUID FK -> repository_snapshots.id  (NOT NULL)
  dimension        text NOT NULL
  old_value        int
  new_value        int
  fired_at         timestamptz NOT NULL
  acknowledged_at  timestamptz
  UNIQUE (rule_id, snapshot_id)
```

Indexes (in migration): `alerts(fired_at DESC)`, `alerts(rule_id)` (implicit via
FK/unique).

### Migration rollback

`alembic downgrade 0002` drops both tables. Both are additive — no data loss on
downgrade/upgrade cycle.

---

## 4. UI states (TrendsPage, route `/projects/:id/trends`)

- **Loading:** centered spinner while trends/rules/alerts fetch.
- **Empty:** "No snapshots yet" empty state with a call to run an analysis; no chart.
- **Error:** error card with retry button (via StateViews).
- **Success:** multi-line chart (Recharts LineChart) with one series per dimension;
  null scores render as gaps. Right rail: rule form + rule list + unacknowledged
  alerts with per-alert Acknowledge button.
- **Insufficient data:** a single snapshot renders a note ("Run another analysis to
  see trends") instead of misleading trend lines.

## 5. Non-goals (deliberately skipped in v1)

- Email/Slack notification delivery — inbox only.
- Cross-project alert inbox pagination (capped at 200).
- Alert rule templates / bulk create.
- Auto-disabling a rule after N fires.
- Editing `enabled` via the PATCH endpoint (schema does not expose it).

## 6. Acceptance checklist

- [ ] `GET /projects/{id}/trends` returns oldest→newest points, gaps for withheld scores.
- [ ] Create rule validates dimension/operator/threshold; duplicate dimension → 409.
- [ ] PATCH/DELETE rule reject rules belonging to another project.
- [ ] Worker fires an alert when a completed snapshot crosses a threshold vs. the previous
      non-null score.
- [ ] `(rule, snapshot)` uniqueness: re-running the same snapshot never duplicates an alert.
- [ ] `GET /alerts` (unacknowledged) shows only member projects' alerts (fixtures in dev).
- [ ] Acknowledge sets `acknowledged_at` and is idempotent.
- [ ] No alert is ever generated from a withheld (coverage < 0.35) score.
- [ ] Writes (create/patch/delete/acknowledge) require auth + membership.
- [ ] Web: chart renders, gaps for null, rule CRUD works, alert list + acknowledge works,
      loading/empty/error states handled.