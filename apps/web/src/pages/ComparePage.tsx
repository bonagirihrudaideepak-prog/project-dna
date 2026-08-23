import { useState } from "react";
import { Card } from "../lib/components";
import { useProjects } from "../hooks/useProjects";
import { ErrorState, LoadingState } from "../components/StateViews";
import type { Project } from "../lib/types";

export const ComparePage = () => {
  const [selected, setSelected] = useState<Project[]>([]);
  // Anonymous-friendly: fetch immediately (backend serves fixtures without auth).
  const { projects, isLoading, isError, error, refetch } = useProjects(undefined, { enabled: true });

  if (isLoading) return <LoadingState />;
  if (isError) {
    return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />;
  }

  const list = projects;

  const toggleProject = (project: Project) => {
    setSelected((prev) => {
      if (prev.some((p) => p.id === project.id)) return prev.filter((p) => p.id !== project.id);
      if (prev.length >= 3) return prev;
      return [...prev, project];
    });
  };

  return (
    <div className="min-h-screen bg-pageBg p-4 md:p-8">
      <h1 className="text-2xl font-bold text-slate-700 mb-6">Compare Projects</h1>

      <div className="mb-6">
        <p className="text-slate-500 text-sm">Select up to 3 projects for comparison:</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {list.map((project) => (
          <Card
            key={project.id}
            className={
              selected.some((p) => p.id === project.id)
                ? "p-4 bg-lavenderSoft border border-lavenderPrimary cursor-pointer"
                : "p-4 hover:shadow-md transition-shadow cursor-pointer"
            }
            onClick={() => toggleProject(project)}
          >
            <div className="flex items-start">
              <div className="w-8 h-8 rounded-md bg-lavenderSoft flex items-center justify-center flex-shrink-0">
                <span className="text-lavenderPrimary text-xs font-medium">{project.name.slice(0, 3)}</span>
              </div>
              <div className="ml-3 flex-1">
                <p className="font-medium text-slate-700 truncate">{project.name || "Unknown"}</p>
                <p className="text-slate-500 text-sm">{project.full_name}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {selected.length > 0 && (
        <div className="mt-6 p-4 bg-lavenderSoft rounded-md">
          <h2 className="text-lg font-medium text-slate-700 mb-4">Comparison Summary</h2>
          <div className="grid grid-cols-2 gap-4">
            {selected.map((project) => (
              <div key={project.id}>
                <p className="text-sm text-slate-500">{project.name || "Unknown"}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ComparePage;