import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button, Card } from "../lib/components";
import { LoadingState } from "../components/StateViews";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import type { GitHubRepo, Project } from "../lib/types";

export const ProjectsPage = ({
  projects,
  loading = false,
  authRequired = false,
}: {
  projects: Project[];
  loading?: boolean;
  authRequired?: boolean;
}) => {
  const navigate = useNavigate();
  const [filter, setFilter] = useState("");
  const [starting, setStarting] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  // Real GitHub repositories accessible with the signed-in user's token.
  const {
    data: ghRepos,
    isLoading: ghLoading,
    isError: ghError,
  } = useQuery<GitHubRepo[]>({
    queryKey: ["github-repos", filter],
    queryFn: () => api.githubRepositories(filter),
    enabled: !authRequired && !loading,
    staleTime: 60_000,
    retry: false,
  });

  const alreadyImported = useMemo(
    () => new Set(projects.map((p) => p.full_name)),
    [projects],
  );

  const startAnalysis = async (repo: GitHubRepo) => {
    setStartError(null);
    setStarting(repo.full_name);
    try {
      const project = await api.importProject(repo.full_name, repo.default_branch);
      await api.queueAnalysis(project.id);
      setStarting(null);
      navigate(`/projects/${project.id}`);
    } catch (e) {
      setStartError(`${repo.full_name}: ${(e as Error).message}`);
      setStarting(null);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="min-h-screen bg-pageBg">
      <header className="pt-8 pb-6 border-b border-borderDefault">
        <h1 className="text-3xl font-bold text-slate-700">Projects</h1>
        <p className="text-slate-500 text-sm mt-1">
          Import a GitHub repository and reconstruct its history.
        </p>
      </header>

      <main className="p-4 md:p-8">
        {authRequired ? (
          <div className="mt-8 max-w-md">
            <Button
              onClick={() => window.location.href = "/api/v1/auth/github/start"}
              className="cta-primary"
            >
              Connect GitHub to get started
            </Button>
          </div>
        ) : (
          <>
            {startError && (
              <div className="card mt mb-4" style={{ borderColor: "var(--error)" }}>
                <span className="badge bad">Error</span> {startError}
              </div>
            )}

            {/* ── Existing analyzed projects ── */}
            {projects.length > 0 && (
              <section className="mb-8">
                <h2 className="text-xl font-bold text-slate-700 mb-3">Your projects</h2>
                <div className="grid grid-cols-1 gap-4">
                  {projects.map((project) => (
                    <a key={project.id} href={`/projects/${project.id}`} style={{ textDecoration: "none" }}>
                      <Card className="p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-start">
                          <div className="w-10 h-10 rounded-md bg-lavenderSoft flex items-center justify-center flex-shrink-0">
                            <span className="text-lavenderPrimary font-medium">
                              {project.name?.slice(0, 3)}
                            </span>
                          </div>
                          <div className="ml-3 flex-1">
                            <p className="font-medium text-slate-700 truncate">
                              {project.name || "Unknown"}
                            </p>
                            <p className="text-slate-500 text-sm">{project.full_name}</p>
                          </div>
                        </div>
                      </Card>
                    </a>
                  ))}
                </div>
              </section>
            )}

            {/* ── GitHub repository picker ── */}
            <section>
              <div className="row between wrap mb-3">
                <h2 className="text-xl font-bold text-slate-700">GitHub repositories</h2>
                <input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="Filter by name…"
                  style={{ maxWidth: 260 }}
                />
              </div>

              {ghLoading ? (
                <LoadingState />
              ) : ghError ? (
                <p className="muted small">
                  Could not load repositories. Check your GitHub connection and retry.
                </p>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {(ghRepos ?? []).map((repo) => (
                    <Card key={repo.github_repo_id ?? repo.full_name} className="p-4">
                      <div className="row between wrap">
                        <div className="flex-1 min-width-0">
                          <p className="font-medium text-slate-700 truncate">{repo.full_name}</p>
                          <p className="text-slate-500 text-sm truncate">
                            {repo.description || "No description"}
                          </p>
                          <span className="badge accent" style={{ marginTop: 4 }}>
                            {repo.visibility}
                          </span>{" "}
                          {alreadyImported.has(repo.full_name) && (
                            <span className="badge ok">imported</span>
                          )}
                        </div>
                        <Button
                          onClick={() => void startAnalysis(repo)}
                          disabled={starting !== null}
                        >
                          {starting === repo.full_name ? "Starting…" : "Analyze"}
                        </Button>
                      </div>
                    </Card>
                  ))}
                  {(ghRepos ?? []).length === 0 && (
                    <p className="muted small">No repositories matched.</p>
                  )}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
};

export default ProjectsPage;
