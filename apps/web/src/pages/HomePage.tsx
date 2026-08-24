import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useQueryClient } from "@tanstack/react-query";
import { PageHeader, PrimaryButton, GhostButton, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { useTrends } from "../hooks/useTrends";
import { useAlerts } from "../hooks/useAlerts";
import { queryKeys } from "../lib/queryKeys";
import { api } from "../lib/api";
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import { DIMENSION_LABELS } from "../lib/format";

const CHART_DIMS = [
  "maintainability",
  "documentation_quality",
  "testing_maturity",
  "delivery_readiness",
] as const;

const DIM_COLOR: Record<string, string> = {
  maintainability: "#6366f1",
  documentation_quality: "#10b981",
  testing_maturity: "#f59e0b",
  delivery_readiness: "#ec4899",
};

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="rounded-xl p-5" style={panelStyle}>
      <div
        style={{
          fontSize: "12px",
          color: C.faint,
          fontWeight: 500,
          marginBottom: "8px",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </div>
      <div style={{ fontFamily: FONT_MONO, fontSize: "28px", fontWeight: 600, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: "12px", color: C.faint, marginTop: "6px" }}>{sub}</div>
    </div>
  );
}

function statusDotColor(status?: string) {
  if (status === "COMPLETED") return C.success;
  if (status === "FAILED") return C.error;
  if (status) return C.lavender;
  return C.faint;
}

export default function HomePage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { user, projects, loading } = useUserAndProjects();
  const { project, projectId } = useActiveProject(projects);
  const { data: trends } = useTrends(projectId);
  const { data: alerts } = useAlerts({ enabled: !!user });
  const [runError, setRunError] = useState<string | null>(null);
  const [queuing, setQueuing] = useState(false);

  // Re-run analysis straight from the dashboard banner.
  const analyzed = projects.filter((p) => p.latest_snapshot?.status === "COMPLETED");

  const chartRows = useMemo(() => {
    return (trends ?? []).map((p) => {
      const row: Record<string, string | number | null> = {
        label: (p.captured_at ?? p.created_at ?? "").slice(0, 10) || p.snapshot_id.slice(0, 8),
      };
      for (const d of CHART_DIMS) row[d] = p.scores?.[d] ?? null;
      return row;
    });
  }, [trends]);

  const lastPoint = trends?.length ? trends[trends.length - 1].scores : undefined;

  const avgScore = useMemo(() => {
    if (!lastPoint) return null;
    const vals = Object.values(lastPoint).filter((v): v is number => v !== null);
    if (!vals.length) return null;
    return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
  }, [lastPoint]);

  const debtRisk = lastPoint?.technical_debt_risk ?? null;

  const runAnalysis = async () => {
    if (!projectId) return;
    setRunError(null);
    setQueuing(true);
    try {
      await api.queueAnalysis(projectId);
      qc.invalidateQueries({ queryKey: queryKeys.snapshots(projectId) });
      qc.invalidateQueries({ queryKey: queryKeys.trends(projectId) });
      // Progress + completion live on the DNA page; land the user there.
      navigate(`/dna?project=${projectId}`);
    } catch (e) {
      setRunError((e as Error).message);
    } finally {
      setQueuing(false);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      {/* Page header */}
      <div className="mb-8">
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: C.ink, letterSpacing: "-0.02em" }}>Dashboard</h1>
        <p style={{ fontSize: "13px", color: C.muted, marginTop: "4px" }}>
          Software archaeology intelligence for{" "}
          <span style={{ fontFamily: FONT_MONO, color: C.lavender }}>
            {user ? user.login : "guest"}
          </span>
        </p>
      </div>

      {!user ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in with GitHub
          </Link>{" "}
          to see your repositories and analyses.
        </EmptyState>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-4 mb-6 lg:grid-cols-4">
            <StatCard
              label="Repositories"
              value={String(projects.length)}
              sub={`${analyzed.length} analyzed`}
              color={C.ink}
            />
            <StatCard
              label="Avg DNA Score"
              value={avgScore === null ? "—" : String(avgScore)}
              sub={project ? project.full_name : "no repository selected"}
              color={C.lavender}
            />
            <StatCard
              label="Open Alerts"
              value={String(alerts?.length ?? 0)}
              sub="threshold breaches"
              color={(alerts?.length ?? 0) > 0 ? C.error : C.success}
            />
            <StatCard
              label="Debt Risk"
              value={debtRisk === null ? "—" : String(debtRisk)}
              sub="lower is better"
              color={C.warning}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-5">
            {/* Score trend chart */}
            <div className="lg:col-span-3 rounded-xl p-5" style={panelStyle}>
              <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
                <div>
                  <h2 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>
                    Score Trend{project ? ` — ${project.name}` : ""}
                  </h2>
                  <p style={{ fontSize: "12px", color: C.faint, marginTop: "2px" }}>
                    {chartRows.length >= 2
                      ? `${chartRows.length} snapshots`
                      : "needs at least two analyses to draw a trend"}
                  </p>
                </div>
                <Link to={`/projects/${projectId}/trends`} style={{ fontSize: "12px", color: C.lavender, textDecoration: "none", fontWeight: 500 }}>
                  Trends & alerts →
                </Link>
              </div>
              {chartRows.length >= 2 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartRows} margin={{ top: 0, right: 4, bottom: 0, left: -24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.borderLight} />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: C.faint, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: C.faint, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}`, fontFamily: "DM Sans" }}
                      itemStyle={{ color: C.body }}
                      labelStyle={{ fontWeight: 600, color: C.ink }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, fontFamily: "DM Sans" }} />
                    {CHART_DIMS.map((d) => (
                      <Line
                        key={d}
                        type="monotone"
                        dataKey={d}
                        name={DIMENSION_LABELS[d]}
                        stroke={DIM_COLOR[d]}
                        strokeWidth={2}
                        dot={false}
                        connectNulls={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 220, display: "flex", alignItems: "center", justifyContent: "center", color: C.faint, fontSize: "13px" }}>
                  Run at least two analyses to see dimension trends.
                </div>
              )}
            </div>

            {/* Recent analyses */}
            <div className="lg:col-span-2 rounded-xl p-5" style={panelStyle}>
              <div className="flex items-center justify-between mb-4">
                <h2 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>Recent Analyses</h2>
                <Link to="/projects" style={{ fontSize: "12px", color: C.lavender, textDecoration: "none", fontWeight: 500 }}>
                  View all →
                </Link>
              </div>
              <div className="space-y-3">
                {projects.slice(0, 6).map((p) => (
                  <Link
                    key={p.id}
                    to={`/dna?project=${p.id}`}
                    className="flex items-center gap-3 p-3 rounded-lg no-underline"
                    style={{
                      backgroundColor: projectId === p.id ? C.lavenderSoft : "#ffffff",
                      border: `1px solid ${projectId === p.id ? C.lavenderMuted : "transparent"}`,
                    }}
                  >
                    <span
                      style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "50%",
                        backgroundColor: statusDotColor(p.latest_snapshot?.status),
                        display: "inline-block",
                        flexShrink: 0,
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <div style={{ fontSize: "13px", fontWeight: 500, color: C.ink, fontFamily: FONT_MONO }}>
                        {p.name}
                      </div>
                      <div style={{ fontSize: "11px", color: C.faint, marginTop: "2px" }}>
                        {p.latest_snapshot?.captured_at
                          ? `Analyzed ${new Date(p.latest_snapshot.captured_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
                          : p.latest_snapshot?.status === "FAILED"
                            ? "Last analysis failed"
                            : "Not yet analyzed"}
                      </div>
                    </div>
                    {p.is_fixture && (
                      <span style={{ fontSize: "10px", color: C.faint, backgroundColor: C.borderLight, padding: "1px 6px", borderRadius: "3px" }}>
                        fixture
                      </span>
                    )}
                  </Link>
                ))}
                {projects.length === 0 && (
                  <p style={{ fontSize: "13px", color: C.muted }}>
                    No repositories yet — add one from Projects or run a fixture analysis.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Quick actions */}
          <div className="mt-6 rounded-xl p-5" style={{ background: "linear-gradient(135deg, #ede9f2 0%, #fce7f3 100%)", border: `1px solid ${C.lavenderMuted}` }}>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>
                  Re-analyze {project ? project.full_name : "a repository"}
                </h3>
                <p style={{ fontSize: "12px", color: C.muted, marginTop: "2px" }}>
                  Queue a fresh snapshot to update DNA scores, timeline, and graph.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <PrimaryButton onClick={() => void runAnalysis()} disabled={!projectId || queuing}>
                  {queuing ? "Queuing…" : "Run Analysis →"}
                </PrimaryButton>
                <Link to="/projects" style={{ textDecoration: "none" }}>
                  <GhostButton>View Projects</GhostButton>
                </Link>
              </div>
            </div>
            {runError && (
              <p className="mt-3 mb-0" style={{ fontSize: "12px", color: C.error }} role="alert">
                {runError}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
