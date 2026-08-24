import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./lib/api";
import { queryKeys } from "./lib/queryKeys";
import NavMenu from "./components/NavMenu";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { LoadingState } from "./components/StateViews";

const HomePage = lazy(() => import("./pages/HomePage").then((m) => ({ default: m.default })));
const LandingPage = lazy(() => import("./pages/LandingPage").then((m) => ({ default: m.default })));
const AuthPage = lazy(() => import("./pages/AuthPage").then((m) => ({ default: m.default })));
const LoginPage = lazy(() => import("./pages/LoginPage").then((m) => ({ default: m.default })));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage").then((m) => ({ default: m.default })));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage").then((m) => ({ default: m.default })));
const ProjectDetailPage = lazy(() =>
  import("./pages/ProjectDetailPage").then((m) => ({ default: m.ProjectDetailPage }))
);
const DNAPage = lazy(() => import("./pages/DNAPage").then((m) => ({ default: m.default })));
const TimelinePage = lazy(() => import("./pages/TimelinePage").then((m) => ({ default: m.default })));
const TrendsPage = lazy(() => import("./pages/TrendsPage").then((m) => ({ default: m.TrendsPage })));
const DecisionsPage = lazy(() => import("./pages/DecisionsPage").then((m) => ({ default: m.default })));
const ExperimentsPage = lazy(() => import("./pages/ExperimentsPage").then((m) => ({ default: m.default })));
const ComparePage = lazy(() => import("./pages/ComparePage").then((m) => ({ default: m.default })));
const GraphPage = lazy(() => import("./pages/GraphPage").then((m) => ({ default: m.default })));
const ExportsPage = lazy(() => import("./pages/ExportsPage").then((m) => ({ default: m.default })));
const MethodologyPage = lazy(() => import("./pages/MethodologyPage").then((m) => ({ default: m.default })));

/** Full-screen marketing/auth routes render without the top nav. */
const FULL_SCREEN_ROUTES = ["/landing", "/auth", "/login"];

/** Legacy /projects/:id/<view> deep links land on the global page for that repo. */
function ProjectRedirect({ view }: { view: string }) {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/${view}?project=${id ?? ""}`} replace />;
}

export default function App() {
  const { data: user } = useQuery({ queryKey: queryKeys.me(), queryFn: api.me, retry: false });

  return (
    <ErrorBoundary>
      <Routes>
        {/* Full-screen routes */}
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Shell routes */}
        <Route
          path="*"
          element={
            <div style={{ minHeight: "100vh", backgroundColor: "#f8fafc" }}>
              <NavMenu user={user ?? null} />
              <main>
                <ErrorBoundary>
                  <Suspense fallback={<LoadingState />}>
                    <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/projects" element={<ProjectsPage />} />
                      <Route path="/projects/:id" element={<ProjectDetailPage />} />
                      <Route path="/projects/:id/trends" element={<TrendsPage />} />
                      <Route path="/projects/:id/dna" element={<ProjectRedirect view="dna" />} />
                      <Route path="/projects/:id/timeline" element={<ProjectRedirect view="timeline" />} />
                      <Route path="/projects/:id/decisions" element={<ProjectRedirect view="decisions" />} />
                      <Route path="/projects/:id/experiments" element={<ProjectRedirect view="experiments" />} />
                      <Route path="/projects/:id/graph" element={<ProjectRedirect view="graph" />} />
                      <Route path="/projects/:id/exports" element={<ProjectRedirect view="exports" />} />
                      <Route path="/dna" element={<DNAPage />} />
                      <Route path="/timeline" element={<TimelinePage />} />
                      <Route path="/compare" element={<ComparePage />} />
                      <Route path="/decisions" element={<DecisionsPage />} />
                      <Route path="/experiments" element={<ExperimentsPage />} />
                      <Route path="/exports" element={<ExportsPage />} />
                      <Route path="/graph" element={<GraphPage />} />
                      <Route path="/methodology" element={<MethodologyPage />} />
                      <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                  </Suspense>
                </ErrorBoundary>
              </main>
            </div>
          }
        />
      </Routes>
    </ErrorBoundary>
  );
}
