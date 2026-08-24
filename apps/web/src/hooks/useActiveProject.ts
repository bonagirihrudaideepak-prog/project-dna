import { useSearchParams } from "react-router-dom";
import type { Project } from "../lib/types";

/**
 * Resolves the "current repository" for global pages via the ?project= search
 * param, falling back to the first analyzed project, then the first project.
 */
export function useActiveProject(projects: Project[]) {
  const [params, setParams] = useSearchParams();
  const requested = params.get("project");

  const active =
    projects.find((p) => p.id === requested) ??
    projects.find((p) => p.latest_snapshot?.status === "COMPLETED") ??
    projects[0] ??
    null;

  const setActive = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("project", id);
    setParams(next, { replace: true });
  };

  return { project: active, projectId: active?.id, setActive };
}
