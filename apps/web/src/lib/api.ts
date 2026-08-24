const BASE = "/api/v1";

import type {
  User,
  DNAScore,
  Project,
  AnalysisJob,
  Snapshot,
  TimelineEvent,
  Decision,
  Experiment,
  GraphData,
  AlertRule,
  Alert,
  TrendPoint,
  Methodology,
  GitHubRepo,
} from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Paths under /api/ are taken verbatim (non-versioned endpoints like
  // /api/methodology); everything else is relative to the versioned base.
  const url = path.startsWith("/api/") ? path : BASE + path;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      message = body?.error?.message || body?.detail || message;
    } catch {
      /* ignore */
    }
    const err = new Error(message) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/auth/me").catch(() => null),
  githubRepositories: (q = "", page = 1) =>
    request<GitHubRepo[]>(
      `/github/repositories?page=${page}` + (q ? `&q=${encodeURIComponent(q)}` : ""),
    ),
  importProject: (fullName: string, branch?: string) =>
    request<Project>("/projects/import", {
      method: "POST",
      body: JSON.stringify({ full_name: fullName, branch }),
    }),
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  queueAnalysis: (projectId: string) =>
    request<AnalysisJob>(`/projects/${projectId}/analyses`, { method: "POST" }),
  job: (id: string) => request<AnalysisJob>(`/analysis-jobs/${id}`),
  snapshots: (projectId: string) =>
    request<Snapshot[]>(`/projects/${projectId}/snapshots`),
  dna: (snapshotId: string) => request<DNAScore[]>(`/snapshots/${snapshotId}/dna`),
  timeline: (snapshotId: string) =>
    request<TimelineEvent[]>(`/snapshots/${snapshotId}/timeline`),
  decisions: (projectId: string) =>
    request<Decision[]>(`/projects/${projectId}/decisions`),
  createDecision: (projectId: string, data: Record<string, unknown>) =>
    request<Decision>(`/projects/${projectId}/decisions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  addOutcomeReview: (id: string, data: Record<string, unknown>) =>
    request<Decision>(`/decisions/${id}/outcome-reviews`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  experiments: (projectId: string) =>
    request<Experiment[]>(`/projects/${projectId}/experiments`),
  createExperiment: (projectId: string, data: Record<string, unknown>) =>
    request<Experiment>(`/projects/${projectId}/experiments`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  compare: (a: string, b: string) =>
    request<Record<string, unknown>>("/comparisons", {
      method: "POST",
      body: JSON.stringify({ snapshot_a: a, snapshot_b: b }),
    }),
  graph: (snapshotId: string, focus?: string, depth = 1) =>
    request<GraphData>(
      `/snapshots/${snapshotId}/graph` + (focus ? `?focus=${encodeURIComponent(focus)}&depth=${depth}` : ""),
    ),
  exportJson: (snapshotId: string) =>
    request<Record<string, unknown>>(`/snapshots/${snapshotId}/exports?fmt=json`, {
      method: "POST",
    }),
  exportHtml: async (snapshotId: string) => {
    const res = await fetch(BASE + `/snapshots/${snapshotId}/exports?fmt=html`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Export failed");
    return res.text();
  },
  trends: (projectId: string) => request<TrendPoint[]>(`/projects/${projectId}/trends`),
  alertRules: (projectId: string) =>
    request<AlertRule[]>(`/projects/${projectId}/alerts`),
  createAlertRule: (projectId: string, data: { dimension: string; operator: "lt" | "gt"; threshold: number }) =>
    request<AlertRule>(`/projects/${projectId}/alerts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteAlertRule: (projectId: string, ruleId: string) =>
    request<{ ok: boolean }>(`/projects/${projectId}/alerts/${ruleId}`, {
      method: "DELETE",
    }),
  alerts: (acknowledged = false) =>
    request<Alert[]>(`/alerts${acknowledged ? "?acknowledged=true" : ""}`),
  acknowledgeAlert: (alertId: string) =>
    request<{ ok: boolean }>(`/alerts/${alertId}/acknowledge`, { method: "POST" }),
  methodology: () => request<Methodology>("/api/methodology"),
};