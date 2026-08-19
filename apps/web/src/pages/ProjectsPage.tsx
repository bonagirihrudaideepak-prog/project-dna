import { Link } from "react-router-dom";
import { Button, Card } from "../lib/components";
import type { Project } from "../lib/types";

export const ProjectsPage = ({ projects }: { projects: Project[] }) => {
  const connected = projects?.length > 0;

  return (
    <div className="min-h-screen bg-pageBg">
      {/* Header */}
      <header className="pt-8 pb-6 border-b border-borderDefault">
        <h1 className="text-3xl font-bold text-slate-700">
          {connected ? "Your Projects" : "Projects"}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Software archaeology & project intelligence platform
        </p>
      </header>

      {/* Main content */}
      <main className="p-4 md:p-8">
        {!connected ? (
          <div className="mt-8 max-w-md">
            <Button
              onClick={() => window.location.href = "/api/v1/auth/github/start"}
              className="cta-primary"
            >
              Connect GitHub to analyze repositories
            </Button>
          </div>
        ) : null}

        {connected && (projects?.length ?? 0) === 0 && (
          <div className="mt-8 text-center">
            <p className="text-slate-500">
              No projects yet.{" "}
              <Button variant="outline" onClick={() => window.location.href = "/api/v1/auth/github/start"}>
                Start your first analysis
              </Button>
            </p>
          </div>
        )}

        {connected && (projects?.length ?? 0) > 0 && (
          <div className="grid grid-cols-1 gap-4">
            {projects!.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                style={{ textDecoration: "none" }}
              >
                <Card className="p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-start">
                    <div
                      className="w-10 h-10 rounded-md bg-lavenderSoft flex items-center justify-center flex-shrink-0"
                    >
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
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default ProjectsPage;