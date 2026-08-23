import { Suspense, lazy } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./lib/api";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { LoadingState } from "./components/StateViews";
import { useProjects } from "./hooks/useProjects";

const HomePage = lazy(() => import("./pages/HomePage").then((m) => ({ default: m.HomePage })));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage").then((m) => ({ default: m.ProjectsPage })));
const ProjectDetailPage = lazy(() =>
  import("./pages/ProjectDetailPage").then((m) => ({ default: m.ProjectDetailPage }))
);
const DNAPage = lazy(() => import("./pages/DNAPage").then((m) => ({ default: m.DNAPage })));
const TimelinePage = lazy(() => import("./pages/TimelinePage").then((m) => ({ default: m.TimelinePage })));
const TrendsPage = lazy(() => import("./pages/TrendsPage").then((m) => ({ default: m.TrendsPage })));
const DecisionsPage = lazy(() => import("./pages/DecisionsPage").then((m) => ({ default: m.DecisionsPage })));
const ExperimentsPage = lazy(() =>
  import("./pages/ExperimentsPage").then((m) => ({ default: m.ExperimentsPage }))
);
const ComparePage = lazy(() => import("./pages/ComparePage").then((m) => ({ default: m.ComparePage })));
const GraphPage = lazy(() => import("./pages/GraphPage").then((m) => ({ default: m.GraphPage })));
const ExportsPage = lazy(() => import("./pages/ExportsPage").then((m) => ({ default: m.ExportsPage })));
const MethodologyPage = lazy(() =>
  import("./pages/MethodologyPage").then((m) => ({ default: m.MethodologyPage }))
);

export default function App() {
  const { data: user } = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });
  const { projects, isLoading: projectsLoading } = useProjects(user?.id);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          Project <span>DNA</span>
        </div>
        {user ? (
          <NavLink className="nav-link" to="/projects">
            Projects
          </NavLink>
        ) : null}
        <NavLink className="nav-link" to="/compare">
          Compare
        </NavLink>
        <NavLink className="nav-link" to="/methodology">
          Methodology
        </NavLink>
        <div className="mt-lg" style={{ fontSize: 13, color: "var(--text-muted)", padding: "0 10px" }}>
          {user ? (
            <>
              Signed in as <strong>{user.login}</strong>
            </>
          ) : (
            <>
              <Link to="/projects">Sign in with GitHub</Link>
            </>
          )}
        </div>
      </aside>
      <main className="main">
        <ErrorBoundary>
          <Suspense fallback={<LoadingState />}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/projects" element={<ProjectsPage projects={projects} loading={projectsLoading} />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route path="/projects/:id/dna" element={<DNAPage />} />
              <Route path="/projects/:id/timeline" element={<TimelinePage />} />
              <Route path="/projects/:id/trends" element={<TrendsPage />} />
              <Route path="/projects/:id/decisions" element={<DecisionsPage />} />
              <Route path="/projects/:id/experiments" element={<ExperimentsPage />} />
              <Route path="/projects/:id/graph" element={<GraphPage />} />
              <Route path="/projects/:id/exports" element={<ExportsPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/methodology" element={<MethodologyPage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  );
}