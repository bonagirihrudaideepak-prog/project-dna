import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, EmptyState } from "../components/StateViews";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import type { GitHubRepo } from "../lib/types";

type Filter = "all" | "analyzed" | "pending";

function StatusBadge({ status }: { status?: string }) {
  const cfg =
    status === "COMPLETED"
      ? { bg: "#d1fae5", text: "#065f46", label: "complete" }
      : status === "FAILED"
        ? { bg: "#fee2e2", text: "#7f1d1d", label: "failed" }
        : status
          ? { bg: "#fef9c3", text: "#713f12", label: status.toLowerCase() }
          : { bg: "#e0f2fe", text: "#075985", label: "never analyzed" };
  return (
    <span
      style={{
        fontSize: "11px",
        fontWeight: 500,
        padding: "3px 8px",
        borderRadius: "4px",
        backgroundColor: cfg.bg,
        color: cfg.text,
      }}
    >
      {cfg.label}
    </span>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user, projects, loading } = useUserAndProjects();
  const [filter, setFilter] = useState<Filter>("all");
  const [repoFilter, setRepoFilter] = useState("");
  const [starting, setStarting] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  const {
    data: ghRepos,
    isLoading: ghLoading,
    isError: ghError,
  } = useQuery<GitHubRepo[]>({
    queryKey: ["github-repos", repoFilter],
    queryFn: () => api.githubRepositories(repoFilter),
    enabled: !!user,
    staleTime: 60_000,
    retry: false,
  });

  const importedNames = useMemo(() => new Set(projects.map((p) => p.full_name)), [projects]);

  const filtered =
    filter === "all"
      ? projects
      : filter === "analyzed"
        ? projects.filter((p) => p.latest_snapshot?.status === "COMPLETED")
        : projects.filter((p) => !p.latest_snapshot || p.latest_snapshot.status !== "COMPLETED");

  const startAnalysis = async (repo: GitHubRepo) => {
    setStartError(null);
    setStarting(repo.full_name);
    try {
      const project = await api.importProject(repo.full_name, repo.default_branch);
      await api.queueAnalysis(project.id);
      qc.invalidateQueries({ queryKey: queryKeys.projects(user?.id ?? null) });
      navigate(`/projects/${project.id}`);
    } catch (e) {
      setStartError(`${repo.full_name}: ${(e as Error).message}`);
      setStarting(null);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <PageHeader title="Projects" subtitle="All repositories in your workspace" />
      </div>

      {!user ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in with GitHub
          </Link>{" "}
          to list your repositories and run analyses.
        </EmptyState>
      ) : (
        <>
          {/* Filters */}
          <div className="flex items-center gap-2 mb-5">
            {(["all", "analyzed", "pending"] as Filter[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer"
                style={{
                  backgroundColor: filter === f ? C.lavenderSoft : C.pageBg,
                  color: filter === f ? C.lavender : C.muted,
                  border: `1px solid ${filter === f ? C.lavenderMuted : C.border}`,
                }}
              >
                {f} ({f === "all" ? projects.length : f === "analyzed" ? analyzedCount(projects) : projects.length - analyzedCount(projects)})
              </button>
            ))}
            <div className="ml-auto">
              <Link to="/auth" style={{ textDecoration: "none" }}>
                <button
                  className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
                  style={{ backgroundColor: C.lavender, color: C.white, border: "none" }}
                >
                  + Add Repository
                </button>
              </Link>
            </div>
          </div>

          {/* Table */}
          {filtered.length === 0 ? (
            <EmptyState>
              No repositories here yet — connect GitHub and analyze your first one below.
            </EmptyState>
          ) : (
            <div className="rounded-xl overflow-hidden mb-10" style={{ border: `1px solid ${C.border}` }}>
              <table style={{ width: "100%", borderCollapse: "collapse", backgroundColor: C.white }}>
                <thead>
                  <tr style={{ backgroundColor: C.pageBg, borderBottom: `1px solid ${C.border}` }}>
                    {["Repository", "Branch", "Last Analyzed", "Status", ""].map((col) => (
                      <th
                        key={col}
                        style={{
                          padding: "10px 16px",
                          fontSize: "11px",
                          fontWeight: 600,
                          color: C.faint,
                          textAlign: "left",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((p, i) => (
                    <tr
                      key={p.id}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = C.pageBg)}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ fontFamily: FONT_MONO, fontSize: "13px", fontWeight: 500, color: C.ink }}>
                          {p.full_name}
                          {p.is_fixture && (
                            <span
                              style={{
                                fontSize: "10px",
                                color: C.faint,
                                backgroundColor: C.borderLight,
                                padding: "1px 6px",
                                borderRadius: "3px",
                                marginLeft: "8px",
                              }}
                            >
                              fixture
                            </span>
                          )}
                        </div>
                        {p.description && (
                          <div style={{ fontSize: "11px", color: C.faint, marginTop: "2px", maxWidth: 420 }} className="truncate">
                            {p.description}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{ fontFamily: FONT_MONO, fontSize: "12px", color: C.muted }}>{p.default_branch}</span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{ fontSize: "12px", color: C.faint }}>
                          {p.latest_snapshot?.captured_at
                            ? new Date(p.latest_snapshot.captured_at).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })
                            : "—"}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <StatusBadge status={p.latest_snapshot?.status} />
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        {p.latest_snapshot?.status === "COMPLETED" ? (
                          <Link
                            to={`/dna?project=${p.id}`}
                            style={{ fontSize: "12px", color: C.lavender, textDecoration: "none", fontWeight: 500 }}
                          >
                            View →
                          </Link>
                        ) : (
                          <Link
                            to={`/projects/${p.id}`}
                            style={{ fontSize: "12px", color: C.lavender, textDecoration: "none", fontWeight: 500 }}
                          >
                            Open →
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Repository picker ── */}
          <section>
            <h2 style={{ fontSize: "16px", fontWeight: 700, color: C.ink, marginBottom: "4px" }}>Analyze a repository</h2>
            <p style={{ fontSize: "13px", color: C.muted, marginBottom: "16px" }}>
              Pick one of your GitHub repositories; Project DNA imports it and queues an analysis.
            </p>

            {startError && (
              <div className="rounded-xl p-4 mb-4" style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", fontSize: "13px", color: "#7f1d1d" }}>
                {startError}
              </div>
            )}

            <input
              value={repoFilter}
              onChange={(e) => setRepoFilter(e.target.value)}
              placeholder="Filter repositories…"
              aria-label="Filter repositories"
              style={{
                width: "100%",
                maxWidth: 320,
                boxSizing: "border-box",
                fontFamily: FONT_MONO,
                fontSize: "13px",
                border: `1px solid ${C.border}`,
                borderRadius: "8px",
                padding: "8px 12px",
                marginBottom: "14px",
                outline: "none",
              }}
            />

            {ghLoading ? (
              <LoadingState label="Loading repositories…" />
            ) : ghError ? (
              <p style={{ fontSize: "13px", color: C.muted }}>Could not load repositories from GitHub.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {(ghRepos ?? []).map((repo) => (
                  <div key={repo.github_repo_id ?? repo.full_name} className="rounded-xl p-4 flex items-start gap-3" style={panelStyle}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span style={{ fontFamily: FONT_MONO, fontSize: "13px", fontWeight: 600, color: C.ink }}>
                          {repo.full_name}
                        </span>
                        <span style={{ fontSize: "10px", color: C.faint, backgroundColor: C.borderLight, padding: "1px 6px", borderRadius: "3px" }}>
                          {repo.visibility}
                        </span>
                        {importedNames.has(repo.full_name) && (
                          <span style={{ fontSize: "10px", fontWeight: 500, backgroundColor: "#d1fae5", color: "#065f46", padding: "1px 6px", borderRadius: "3px" }}>
                            imported
                          </span>
                        )}
                      </div>
                      {repo.description && (
                        <p className="truncate" style={{ fontSize: "11px", color: C.faint, marginTop: "4px", marginBottom: 0 }}>
                          {repo.description}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => void startAnalysis(repo)}
                      disabled={starting !== null}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer flex-shrink-0"
                      style={{
                        backgroundColor: starting === repo.full_name ? C.lavenderMuted : C.lavender,
                        color: C.white,
                        border: "none",
                        cursor: starting !== null ? "not-allowed" : "pointer",
                      }}
                    >
                      {starting === repo.full_name ? "Starting…" : "Analyze"}
                    </button>
                  </div>
                ))}
                {(ghRepos ?? []).length === 0 && <p style={{ fontSize: "13px", color: C.muted }}>No repositories matched.</p>}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function analyzedCount(projects: { latest_snapshot?: { status?: string } | null }[]) {
  return projects.filter((p) => p.latest_snapshot?.status === "COMPLETED").length;
}
