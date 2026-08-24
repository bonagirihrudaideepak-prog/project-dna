import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card } from "../lib/components";
import { LoadingState } from "../components/StateViews";
import { api } from "../lib/api";
import type { Project } from "../lib/types";

// Offline demo repositories shipped with the API (fixture mode).
const DEMO_REPOS = [
  { full_name: "student/minimal-app", label: "Minimal app", blurb: "Analyze a tiny repo in seconds" },
  { full_name: "team/wardrobe-api", label: "Mature API", blurb: "Tests, CI, docs, migrations" },
  { full_name: "student/evolution-app", label: "Evolution", blurb: "History across many snapshots" },
];

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
  const [starting, setStarting] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  if (loading) return <LoadingState />;

  const startDemo = async (fullName: string) => {
    setStartError(null);
    setStarting(fullName);
    try {
      // Import returns the project (existing or newly created); queueing an
      // analysis gives the worker something to do immediately.
      const project = await api.importProject(fullName);
      await api.queueAnalysis(project.id);
      setStarting(null);
      navigate(`/projects/${project.id}`);
    } catch (e) {
      setStartError((e as Error).message);
      setStarting(null);
    }
  };

  return (
    <div className="min-h-screen bg-pageBg">
      {/* Header */}
      <header className="pt-8 pb-6 border-b border-borderDefault">
        <h1 className="text-3xl font-bold text-slate-700">
          {projects.length > 0 ? "Your Projects" : "Projects"}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Software archaeology &amp; project intelligence platform
        </p>
      </header>

      {/* Main content */}
      <main className="p-4 md:p-8">
        {authRequired ? (
          <div className="mt-8 max-w-md">
            <Button
              onClick={() => window.location.href = "/api/v1/auth/github/start"}
              className="cta-primary"
            >
              Connect GitHub to analyze repositories
            </Button>
          </div>
        ) : (
          <>
            {projects.length === 0 && (
              <p className="muted mb-4">No projects yet. Start with a demo repository:</p>
            )}

            {!authRequired && projects.length === 0 && (
              <section className="mb-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {DEMO_REPOS.map((repo) => (
                    <Card key={repo.full_name} className="p-6 hover:shadow-md transition-shadow">
                      <h3 className="font-medium text-lavenderPrimary">{repo.label}</h3>
                      <p className="text-slate-500 text-sm mt-1 mb-4">{repo.blurb}</p>
                      <Button onClick={() => void startDemo(repo.full_name)} disabled={starting !== null}>
                        {starting === repo.full_name ? "Starting…" : "Analyze"}
                      </Button>
                    </Card>
                  ))}
                </div>
                {startError && <p className="small bad mt-2">{startError}</p>}
              </section>
            )}

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
          </>
        )}
      </main>
    </div>
  );
};

export default ProjectsPage;
