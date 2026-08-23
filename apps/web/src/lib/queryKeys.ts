/**
 * Central TanStack Query key registry.
 *
 * Query keys must only be constructed here so cache reads, writes, and
 * invalidations stay in sync. Colliding-but-different keys previously caused
 * duplicate fetches and stale caches.
 */

export const queryKeys = {
  me: () => ["me"] as const,
  projects: (userId?: string | null) => ["projects", userId ?? null] as const,
  project: (projectId: string | null | undefined) => ["project", projectId ?? null] as const,
  snapshots: (projectId: string | null | undefined) => ["snapshots", projectId ?? null] as const,
  snapshot: (snapshotId: string | null | undefined) => ["snapshot", snapshotId ?? null] as const,
  analysis: (snapshotId: string | null | undefined) => ["analysis", snapshotId ?? null] as const,
  timeline: (snapshotId: string | null | undefined) => ["timeline", snapshotId ?? null] as const,
  comparison: (a: string | null | undefined, b: string | null | undefined) => ["comparison", a, b] as const,
  trends: (projectId: string | null | undefined) => ["trends", projectId ?? null] as const,
  alerts: () => ["alerts"] as const,
  alertRules: (projectId: string | null | undefined) => ["alert-rules", projectId ?? null] as const,
  graph: (snapshotId: string | null | undefined) => ["graph", snapshotId ?? null] as const,
  decisions: (projectId: string | null | undefined) => ["decisions", projectId ?? null] as const,
  experiments: (projectId: string | null | undefined) => ["experiments", projectId ?? null] as const,
};
