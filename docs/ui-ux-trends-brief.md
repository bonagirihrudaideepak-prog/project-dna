# UI/UX Brief — Trends & Alerts Dashboard

Design brief for the Trends & Alerts screen (`/projects/:id/trends`). Pairs with
`docs/spec-trends-alerts.md`. Current implementation matches this brief; use it as the
reference when the screen evolves.

Audience: engineering leads inspecting a project's health over time. Power users —
they compare many projects, so density over decoration.

Brand: dark-neutral scientific dashboard. Existing tokens: `--bg-page` page background,
`--text` slate-700, card surfaces, `accent` badge, `badge`, `muted` secondary text,
`row between`, `grid grid-2` responsive grid, `card mt/mb` spacing helpers.

---

## 1. User journey

1. User lands from ProjectDetailPage's "View trends" card link.
2. Page loads in three sections: header, trend chart, then rules + alerts side by side.
3. User reads the chart to spot a dimension drifting (e.g. maintainability declining).
4. User creates a rule: pick dimension, operator (below/above), threshold → Add rule.
5. Later, the worker fires an alert; user returns, sees it in the Alerts panel, clicks
   Acknowledge to clear it.

## 2. Layout per screen

- **Header:** H1 "Trends & Alerts", one-line description, "Back to DNA profile" link
  (top-right). 8px padding on mobile, 32px on ≥768px.
- **Chart section (full width card):** `ResponsiveContainer` fixed 360px height,
  LineChart with CartesianGrid, YAxis 0–100, XAxis = snapshot date labels, Legend.
  One line per dimension (8 total), fixed palette, no dots, `connectNulls=false`.
- **Rules + Alerts (below, `grid grid-2`, stacks on mobile):**
  - Left card — **Alert rules**: rule list (dimension, below/above N, Delete) + inline
    create form (dimension select, operator select, threshold number, Add rule).
  - Right card — **Alerts**: active alerts list (dimension badge, new value, "(was N)",
    Acknowledge).

## 3. Component inventory & states

| Component | States |
| --------- | ------ |
| Chart | Loading (spinner) · Error (retry) · Empty/insufficient (<2 snapshots → info card) · Success (lines, gaps for withheld) |
| Rule list item | Default · Delete pending (button disabled) |
| Rule form | Default · Submitting (Add disabled) · Server error (inline `formError` text) |
| Alert item | Default · Acknowledge pending (button disabled) |

## 4. Typography & color tokens

- Typography: existing app stack (slate-700 headings, `text-sm` slate-500 secondary,
  `muted small` hints, `font-bold` for rule dimension).
- Chart palette (fixed per dimension, never derived):
  - technical_complexity `#6b7280`, maintainability `#3b82f6`, testing_maturity
    `#10b981`, documentation_quality `#f59e0b`, evolution_health `#8b5cf6`,
    delivery_readiness `#ef4444`, scalability_readiness `#14b8a6`,
    technical_debt_risk `#f97316`.
- Semantic: `accent` badge for alert dimension, `badge` for neutral chips, `bad` for
  inline form errors.

## 5. Motion

- No bespoke animation. Standard: button hover/active transitions, Recharts default
  line draw. Alert/rule list updates render immediately (TanStack Query refetch).

## 6. Accessibility

- Form controls are native `<select>`/`<input>` with `<label>`-adjacent placement;
  numbers constrained to 0–100 via `min`/`max`.
- Chart is data + text: the rules/alerts panels carry the same facts, so no information
  is lost without the chart. Tooltip is keyboard-reachable via Recharts defaults.
- Contrast: slate-700 on page background passes AA; muted text remains 12px+.
- Error/empty states use text, not color alone.

## 7. Reference patterns (direction only, not copied)

- GitHub Insights trend graphs — dense multi-series, sparse decoration.
- Datadog dashboards — fixed metric palette, gaps meaningfully rendered.
- Linear activity graphs — subdued grid, readable legend.