import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ErrorState, LoadingState } from "../components/StateViews";
import type { Project } from "../lib/types";

export function ProjectsPage() {
  const [query, setQuery] = useState("");
  const qc = useQueryClient();
  const {
    data: repos,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["repos", query],
    queryFn: () => api.repositories(query),
  });
  const { data: projects, isError: projectsError } = useQuery({
    queryKey: ["projects"],
    queryFn: api.projects,
  });

  const importMutation = useMutation({
    mutationFn: (full_name: string) => api.importProject(full_name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (projectId: string) => api.queueAnalysis(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  return (
    <div>
      <h1>Connect a repository</h1>
      <div className="two-col">
        <div>
          <label htmlFor="repo-search">Search GitHub repositories</label>
          <input
            id="repo-search"
            placeholder="Search GitHub repositories…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Branch</th>
                  <th>Description</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(repos ?? []).map((r) => (
                  <tr key={r.full_name}>
                    <td>
                      <strong>{r.full_name}</strong>
                      <div className="small muted">{r.is_fixture ? "fixture" : "github"}</div>
                    </td>
                    <td>{r.default_branch}</td>
                    <td className="small muted">{r.description}</td>
                    <td>
                      <button
                        disabled={importMutation.isPending || analyzeMutation.isPending}
                        onClick={() => {
                          importMutation.mutate(r.full_name);
                        }}
                      >
                        Import
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {importMutation.isSuccess && (
            <div className="card mt">
              <p>
                Imported <strong>{importMutation.data.full_name}</strong>. Analyze it now.
              </p>
              <button onClick={() => analyzeMutation.mutate(importMutation.data.id)}>
                Run analysis →
              </button>
              {analyzeMutation.isSuccess && (
                <p className="small muted mt">
                  Analysis queued (job {analyzeMutation.data.id.slice(0, 8)}). View the project to follow
                  progress.
                </p>
              )}
            </div>
          )}
        </div>
        <div>
          <h3 className="mb">Your projects</h3>
          {projectsError && (
            <ErrorState message="Could not load projects" onRetry={() => qc.invalidateQueries({ queryKey: ["projects"] })} />
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(projects ?? []).map((p: Project) => (
              <a key={p.id} href={`/projects/${p.id}`} className="card" style={{ color: "var(--text)" }}>
                <strong>{p.full_name}</strong>
                <div className="small muted">
                  {p.latest_snapshot
                    ? `Snapshot ${p.latest_snapshot.status}`
                    : "No snapshot yet"}
                </div>
              </a>
            ))}
            {(projects ?? []).length === 0 && (
              <p className="muted small">No projects imported yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}