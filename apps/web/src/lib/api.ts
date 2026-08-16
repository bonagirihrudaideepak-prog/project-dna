const BASE = "/api/v1";

import type { User, ScoredDimension, ApiListResponse } from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
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
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/auth/me").catch(() => null),
  repositories: (q = "") =>
    request<Project[]>(
      "/github/repositories" + (q ? `?q=${encodeURIComponent(q)}` : ""),
    ),
  importProject: (full_name: string, branch?: string) =>
    request<Project>("/projects/import", {
      method: "POST",
      body: JSON.stringify({ full_name, branch }),
    }),
  projects: () => request<ApiListResponse<Project>>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  queueAnalysis: (projectId: string) =>
    request<AnalysisJob>(`/projects/${projectId}/analyses`, { method: "POST" }),
  job: (id: string) => request<AnalysisJob>(`/analysis-jobs/${id}`),
  snapshots: (projectId: string) =>
    request<ApiListResponse<Snapshot>>(`/projects/${projectId}/snapshots`),
  dna: (snapshotId: string) => request<ScoredDimension[]>(`/snapshots/${snapshotId}/dna`),
  timeline: (snapshotId: string) =>
    request<TimelineEvent[]>(`/snapshots/${snapshotId}/timeline`),
  decisions: (projectId: string) =>
    request<ApiListResponse<Decision>>(`/projects/${projectId}/decisions`),
  createDecision: (projectId: string, data: Record<string, unknown>) =>
    request<Decision>(`/projects/${projectId}/decisions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateDecision: (id: string, data: Record<string, unknown>) =>
    request<Decision>(`/decisions/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  addOutcomeReview: (id: string, data: Record<string, unknown>) =>
    request<Decision>(`/decisions/${id}/outcome-reviews`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  experiments: (projectId: string) =>
    request<ApiListResponse<Experiment>>(`/projects/${projectId}/experiments`),
  createExperiment: (projectId: string, data: Record<string, unknown>) =>
    request<Experiment>(`/projects/${projectId}/experiments`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateExperiment: (id: string, data: Record<string, unknown>) =>
    request<Experiment>(`/experiments/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  compare: (a: string, b: string) =>
    request<Record<string, unknown>>("/comparisons", {
      method: "POST",
      body: JSON.stringify({ snapshot_a: a, snapshot_b: b }),
    }),
  graph: (snapshotId: string, focus?: string, depth = 1) =>
    request<GraphData>(
      `/snapshots/${snapshotId}/graph` + (focus ? `?focus=${encodeURIComponent(focus)}&depth=${depth}` : ""),
    ),
  summary: (snapshotId: string) =>
    request<Record<string, unknown>>(`/snapshots/${snapshotId}/summaries`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
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
};