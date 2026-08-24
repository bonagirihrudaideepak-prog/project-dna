import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import DimensionCard from "../components/DimensionCard";
import { PageHeader, ProjectSelector, PrimaryButton, GhostButton, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { useDNA } from "../hooks/useDNA";
import { useJob, useSnapshotId } from "../hooks/useJob";
import { useMethodology } from "../hooks/useMethodology";
import { useTrends } from "../hooks/useTrends";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { useQueryClient } from "@tanstack/react-query";
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import { DIMENSION_LABELS } from "../lib/format";
import type { DNAScore, ScoredDimension } from "../lib/types";

function limitationsOf(d: DNAScore): string[] {
  const direct = (d as ScoredDimension).limitations;
  if (Array.isArray(direct)) return direct;
  const expl = d.explanation?.limitations;
  return Array.isArray(expl) ? (expl as string[]) : [];
}

/** Derive a coarse per-dimension trend by comparing the last two snapshots. */
function trendFor(dim: string, trends: { scores: Record<string, number | null> }[] | undefined): "up" | "down" | "stable" | undefined {
  if (!trends || trends.length < 2) return undefined;
  const prev = trends[trends.length - 2].scores?.[dim];
  const curr = trends[trends.length - 1].scores?.[dim];
  if (prev === null || prev === undefined || curr === null || curr === undefined) return undefined;
  if (curr > prev) return "up";
  if (curr < prev) return "down";
  return "stable";
}

export default function DNAPage() {
  const qc = useQueryClient();
  const { user, projects, loading: spineLoading } = useUserAndProjects();
  const { project, projectId, setActive } = useActiveProject(projects);
  const { snapshotId, loading: snapLoading } = useSnapshotId(projectId);
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useDNA(snapshotId);
  const { data: methodology } = useMethodology();
  const { data: trends } = useTrends(projectId);

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [justFinished, setJustFinished] = useState(false);
  const { job } = useJob(jobId, () => {
    setJobId(null);
    setJustFinished(true);
    qc.invalidateQueries({ queryKey: queryKeys.snapshots(projectId) });
    qc.invalidateQueries({ queryKey: queryKeys.analysis(snapshotId) });
    refetch();
  });

  const scores = useMemo(() => data ?? [], [data]);

  const dimDescriptions = useMemo(() => {
    const m = new Map<string, string>();
    for (const d of methodology?.dimensions ?? []) m.set(d.key, d.description);
    return m;
  }, [methodology]);

  const radarData = useMemo(
    () =>
      scores
        .filter((d) => d.score !== null)
        .map((d) => ({
          subject: (DIMENSION_LABELS[d.dimension] ?? d.dimension).split(" ")[0],
          score:
            d.direction === "lower_is_better" && d.score !== null ? 100 - d.score : d.score ?? 0,
        })),
    [scores]
  );

  const avgScore = useMemo(() => {
    const effective = scores.map((d) =>
      d.direction === "lower_is_better" && d.score !== null ? 100 - d.score : d.score
    );
    const vals = effective.filter((v): v is number => v !== null);
    if (!vals.length) return null;
    return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
  }, [scores]);

  const runAnalysis = async () => {
    if (!projectId) return;
    setJobError(null);
    setJustFinished(false);
    try {
      const j = await api.queueAnalysis(projectId);
      setJobId(j.id);
    } catch (e) {
      setJobError((e as Error).message);
    }
  };

  if (spineLoading || snapLoading || isLoading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader title="DNA Analysis" subtitle="8-dimension codebase intelligence profile" />

      {!user ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in with GitHub
          </Link>{" "}
          to analyze repositories and view their DNA profile.
        </EmptyState>
      ) : projects.length === 0 ? (
        <EmptyState>
          No repositories yet — import one from{" "}
          <Link to="/projects" style={{ color: C.lavender, fontWeight: 600 }}>
            Projects
          </Link>{" "}
          to see its DNA profile.
        </EmptyState>
      ) : (
        <>
          {/* Repo selector + run analysis */}
          <div className="rounded-xl p-4 mb-6 flex items-end gap-3 flex-wrap" style={panelStyle}>
            <ProjectSelector value={projectId ?? ""} projects={projects} onChange={setActive} />
            <PrimaryButton onClick={() => void runAnalysis()} disabled={!!jobId}>
              {jobId ? `Analyzing… ${Math.round(job?.progress ?? 0)}%` : "Run Analysis"}
            </PrimaryButton>
            <div style={{ paddingBottom: "4px" }}>
              {snapshotId ? (
                <span style={{ fontSize: "11px", color: C.success, fontWeight: 500 }}>
                  ● Snapshot {snapshotId.slice(0, 8)} ready
                </span>
              ) : (
                <span style={{ fontSize: "11px", color: C.faint, fontWeight: 500 }}>
                  ○ No completed snapshot yet
                </span>
              )}
            </div>
          </div>

          {(jobError || job?.state === "FAILED") && (
            <ErrorState message={(job?.error_detail || jobError || "Analysis failed")} />
          )}

          {justFinished && !jobId && (
            <div
              className="rounded-xl px-4 py-3 mb-6 flex items-center gap-3"
              style={{ backgroundColor: "#d1fae5", border: "1px solid #6ee7b7", fontSize: "13px", color: "#065f46" }}
              role="status"
            >
              <strong>✓ Analysis complete</strong>
              <span>Latest snapshot is shown below{snapshotId ? ` (${snapshotId.slice(0, 8)})` : ""}.</span>
              <button
                onClick={() => setJustFinished(false)}
                className="ml-auto text-xs font-medium cursor-pointer"
                style={{ background: "none", border: "none", color: "#065f46", padding: 0 }}
              >
                Dismiss
              </button>
            </div>
          )}

          {job && jobId && (
            <div className="rounded-xl p-4 mb-6" style={panelStyle}>
              <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: "13px", fontWeight: 600, color: C.ink }}>Analysis running…</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.lavender }}>{job.state}</span>
              </div>
              <div className="rounded-full overflow-hidden" style={{ height: "6px", backgroundColor: C.borderLight }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${job.progress}%`, backgroundColor: C.lavender }}
                />
              </div>
              {job.phase && <p style={{ fontSize: "12px", color: C.muted, marginTop: "6px" }}>{job.phase}</p>}
            </div>
          )}

          {!snapshotId ? (
            <EmptyState>No completed analysis for this repository yet — hit “Run Analysis” above.</EmptyState>
          ) : scores.length === 0 ? (
            <EmptyState>No scores recorded for this snapshot.</EmptyState>
          ) : (
            <>
              <div className="grid gap-6 lg:grid-cols-5">
                {/* Radar chart */}
                <div className="lg:col-span-2 rounded-xl p-6" style={panelStyle}>
                  <div className="text-center mb-2">
                    <div style={{ fontFamily: FONT_MONO, fontSize: "48px", fontWeight: 700, color: C.lavender, lineHeight: 1 }}>
                      {avgScore ?? "—"}
                    </div>
                    <div style={{ fontSize: "12px", color: C.faint, marginTop: "4px" }}>Overall DNA Score</div>
                  </div>
                  {radarData.length >= 3 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                        <PolarGrid stroke={C.borderLight} />
                        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: C.faint, fontFamily: "DM Sans" }} />
                        <Tooltip
                          contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}` }}
                          formatter={(val: number) => [`${val}`, "Score"]}
                        />
                        <Radar name="DNA Score" dataKey="score" stroke={C.lavender} fill={C.lavender} fillOpacity={0.15} strokeWidth={2} />
                      </RadarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: C.faint, fontSize: "12px", textAlign: "center" }}>
                      Not enough scored dimensions to draw the radar.
                    </div>
                  )}

                  {/* Legend */}
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {[
                      { label: "High confidence", color: "#10b981" },
                      { label: "Moderate", color: "#f59e0b" },
                      { label: "Low confidence", color: "#f97316" },
                      { label: "Insufficient", color: "#ef4444" },
                    ].map((item) => (
                      <div key={item.label} className="flex items-center gap-2">
                        <span style={{ width: "8px", height: "8px", borderRadius: "2px", backgroundColor: item.color, flexShrink: 0 }} />
                        <span style={{ fontSize: "11px", color: C.faint }}>{item.label}</span>
                      </div>
                    ))}
                  </div>

                  {/* Indicator breakdown for expandable cards lives in DimensionCard; keep exports here */}
                  <div className="flex items-center justify-center gap-3 mt-5 flex-wrap">
                    <Link to={`/exports?project=${projectId}`} style={{ textDecoration: "none" }}>
                      <GhostButton>Export report</GhostButton>
                    </Link>
                    <Link to={`/compare?project=${projectId}`} style={{ textDecoration: "none" }}>
                      <GhostButton>Compare</GhostButton>
                    </Link>
                  </div>
                </div>

                {/* Dimension cards */}
                <div className="lg:col-span-3">
                  <div className="grid gap-3">
                    {scores.map((d) => (
                      <DimensionCard
                        key={d.dimension}
                        dim={{
                          name: DIMENSION_LABELS[d.dimension] ?? d.dimension,
                          score: d.score,
                          confidence: d.confidence,
                          direction: d.direction,
                          description: dimDescriptions.get(d.dimension),
                          limitations: limitationsOf(d),
                          trend: trendFor(d.dimension, trends),
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
