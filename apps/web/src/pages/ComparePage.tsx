import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { DIMENSION_LABELS } from "../lib/format";
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import type { Project, Snapshot } from "../lib/types";

interface PerDimension {
  dimension: string;
  a: number;
  b: number;
  abs_delta: number;
}
interface CompareResult {
  similarity: number | null;
  distance: number | null;
  used_dimensions: string[];
  excluded_dimensions: string[];
  similarity_coverage: number;
  model_compatible: boolean;
  per_dimension?: PerDimension[];
}

const COLORS = ["#6366f1", "#10b981"];

function ProjectPicker({
  label,
  projects,
  value,
  onChange,
}: {
  label: string;
  projects: Project[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div>
      <label style={{ fontSize: "11px", fontWeight: 500, color: C.faint, display: "block", marginBottom: "4px" }}>
        {label}
      </label>
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          boxSizing: "border-box",
          fontFamily: FONT_MONO,
          fontSize: "13px",
          border: `1px solid ${C.border}`,
          borderRadius: "8px",
          padding: "8px 12px",
          color: C.ink,
          backgroundColor: C.white,
          outline: "none",
        }}
      >
        <option value="">Select a project…</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.full_name}
          </option>
        ))}
      </select>
    </div>
  );
}

function SnapshotPicker({
  projectId,
  value,
  onChange,
}: {
  projectId: string;
  value: string;
  onChange: (sid: string) => void;
}) {
  const { data: snaps, isLoading } = useQuery<Snapshot[]>({
    queryKey: queryKeys.snapshots(projectId),
    queryFn: () => api.snapshots(projectId),
    enabled: !!projectId,
    staleTime: 30_000,
  });
  if (!projectId) return null;
  if (isLoading) return <p style={{ fontSize: "12px", color: C.faint }}>Loading snapshots…</p>;
  const completed = (snaps ?? []).filter((s) => s.status === "COMPLETED");
  if (completed.length === 0)
    return <p style={{ fontSize: "12px", color: C.warning }}>No completed analysis yet — run one first.</p>;
  return (
    <select
      aria-label="Select snapshot"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        width: "100%",
        boxSizing: "border-box",
        fontFamily: FONT_MONO,
        fontSize: "12px",
        border: `1px solid ${C.border}`,
        borderRadius: "8px",
        padding: "8px 12px",
        color: C.ink,
        backgroundColor: C.white,
        outline: "none",
        marginTop: "8px",
      }}
    >
      {!value && <option value="">Select snapshot…</option>}
      {completed.map((s) => (
        <option key={s.id} value={s.id}>
          {new Date(s.captured_at ?? Date.now()).toLocaleString()} ({s.id.slice(0, 8)})
        </option>
      ))}
    </select>
  );
}

export default function ComparePage() {
  const { user, projects, loading } = useUserAndProjects();
  const [aProject, setAProject] = useState("");
  const [bProject, setBProject] = useState("");
  const [aSnap, setASnap] = useState("");
  const [bSnap, setBSnap] = useState("");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const ready = aSnap !== "" && bSnap !== "";

  const runCompare = async () => {
    setCompareError(null);
    setComparing(true);
    try {
      const res = await api.compare(aSnap, bSnap);
      setResult(res as unknown as CompareResult);
    } catch (e) {
      setCompareError((e as Error).message);
      setResult(null);
    } finally {
      setComparing(false);
    }
  };

  const exportReport = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `comparison-${result.similarity ?? "na"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const projectName = useMemo(() => {
    const m = new Map((projects ?? []).map((p) => [p.id, p.full_name]));
    return (id: string) => m.get(id) ?? id.slice(0, 8);
  }, [projects]);

  const chartData = useMemo(
    () =>
      (result?.per_dimension ?? []).map((d) => ({
        dimension: (DIMENSION_LABELS[d.dimension] ?? d.dimension).replace(/ Readiness| Quality|Maturity/, ""),
        a: d.a,
        b: d.b,
      })),
    [result]
  );

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader title="Compare" subtitle="Side-by-side DNA dimension comparison across snapshots" />

      {!user ? (
        <EmptyState>Sign in with GitHub to compare analyses.</EmptyState>
      ) : projects.length === 0 ? (
        <EmptyState>No repositories yet — run analyses on at least two repositories to compare.</EmptyState>
      ) : (
        <>
          {/* Pickers */}
          <div className="rounded-xl p-5 mb-6 grid gap-4 md:grid-cols-2" style={panelStyle}>
            <div>
              <ProjectPicker label="SNAPSHOT A" projects={projects} value={aProject} onChange={(id) => { setAProject(id); setASnap(""); }} />
              <SnapshotPicker projectId={aProject} value={aSnap} onChange={setASnap} />
            </div>
            <div>
              <ProjectPicker label="SNAPSHOT B" projects={projects} value={bProject} onChange={(id) => { setBProject(id); setBSnap(""); }} />
              <SnapshotPicker projectId={bProject} value={bSnap} onChange={setBSnap} />
            </div>
            <div className="md:col-span-2 flex items-center justify-between gap-3 flex-wrap">
              <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>
                Comparable dimensions require ≥ 60% coverage on both sides.
              </span>
              <button
                onClick={() => void runCompare()}
                disabled={!ready || comparing}
                className="px-5 py-2 rounded-lg text-sm font-semibold cursor-pointer"
                style={{
                  backgroundColor: ready && !comparing ? C.lavender : C.lavenderMuted,
                  color: C.white,
                  border: "none",
                  cursor: !ready || comparing ? "not-allowed" : "pointer",
                }}
              >
                {comparing ? "Comparing…" : "Compare"}
              </button>
            </div>
          </div>

          {compareError && <ErrorState message={compareError} />}

          {result && (
            <>
              {/* Repo badges */}
              <div className="flex items-center gap-3 mb-6 flex-wrap">
                {[{ id: aProject, name: projectName(aProject), snap: aSnap }, { id: bProject, name: projectName(bProject), snap: bSnap }].map((r, i) => (
                  <div key={r.snap} className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={panelStyle}>
                    <span style={{ width: "10px", height: "10px", borderRadius: "2px", backgroundColor: COLORS[i], flexShrink: 0 }} />
                    <span style={{ fontFamily: FONT_MONO, fontSize: "12px", color: C.ink }}>{r.name}</span>
                  </div>
                ))}
              </div>

              {/* Summary chips */}
              <div className="flex items-center gap-3 mb-6 flex-wrap">
                <span style={{ fontSize: "12px", fontWeight: 600, padding: "4px 10px", borderRadius: "6px", backgroundColor: C.lavenderSoft, color: C.lavender }}>
                  similarity {result.similarity ?? "n/a"}%
                </span>
                {result.distance != null && (
                  <span style={{ fontSize: "12px", fontWeight: 500, padding: "4px 10px", borderRadius: "6px", backgroundColor: C.pageBg, border: `1px solid ${C.border}`, color: C.muted }}>
                    distance {result.distance}
                  </span>
                )}
                <span style={{ fontSize: "12px", fontWeight: 500, padding: "4px 10px", borderRadius: "6px", backgroundColor: C.pageBg, border: `1px solid ${C.border}`, color: C.muted }}>
                  coverage {Math.round(result.similarity_coverage * 100)}%
                </span>
                {!result.model_compatible && (
                  <span style={{ fontSize: "12px", fontWeight: 600, padding: "4px 10px", borderRadius: "6px", backgroundColor: "#fef9c3", color: "#713f12" }}>
                    model mismatch
                  </span>
                )}
              </div>

              {/* Grouped bar chart */}
              {(result.per_dimension ?? []).length > 0 && (
                <div className="rounded-xl p-6 mb-6" style={panelStyle}>
                  <h2 style={{ fontSize: "14px", fontWeight: 600, color: C.ink, marginBottom: "20px" }}>All Dimensions</h2>
                  <ResponsiveContainer width="100%" height={340}>
                    <BarChart data={chartData} margin={{ top: 0, right: 4, bottom: 0, left: -24 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={C.borderLight} />
                      <XAxis dataKey="dimension" tick={{ fontSize: 10, fill: C.faint, fontFamily: "DM Sans" }} axisLine={false} tickLine={false} interval={0} angle={-14} dy={8} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: C.faint, fontFamily: FONT_MONO }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}`, fontFamily: "DM Sans" }}
                        labelStyle={{ fontWeight: 600, color: C.ink }}
                      />
                      <Legend wrapperStyle={{ fontSize: 11, fontFamily: "DM Sans" }} />
                      <Bar dataKey="a" name={projectName(aProject)} fill={COLORS[0]} radius={[3, 3, 0, 0]} />
                      <Bar dataKey="b" name={projectName(bProject)} fill={COLORS[1]} radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Comparison table */}
              {(result.per_dimension ?? []).length > 0 ? (
                <div className="rounded-xl overflow-hidden mb-4" style={{ border: `1px solid ${C.border}` }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", backgroundColor: C.white }}>
                    <thead>
                      <tr style={{ backgroundColor: C.pageBg, borderBottom: `1px solid ${C.border}` }}>
                        {["Dimension", projectName(aProject), projectName(bProject), "|Δ|"].map((col, i) => (
                          <th
                            key={i}
                            style={{
                              padding: "10px 16px",
                              fontSize: "11px",
                              fontWeight: 600,
                              color: i > 0 && i < 3 ? COLORS[i - 1] : C.faint,
                              textAlign: i === 0 ? "left" : "center",
                              textTransform: "uppercase",
                              letterSpacing: "0.04em",
                            }}
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.per_dimension!.map((d, i) => (
                        <tr key={d.dimension} style={{ borderBottom: i < result.per_dimension!.length - 1 ? `1px solid ${C.borderLight}` : "none" }}>
                          <td style={{ padding: "12px 16px", fontSize: "13px", fontWeight: 500, color: C.ink }}>
                            {DIMENSION_LABELS[d.dimension] ?? d.dimension}
                          </td>
                          <td style={{ padding: "12px 16px", textAlign: "center", fontFamily: FONT_MONO, fontSize: "14px", color: COLORS[0] }}>{d.a}</td>
                          <td style={{ padding: "12px 16px", textAlign: "center", fontFamily: FONT_MONO, fontSize: "14px", color: COLORS[1] }}>{d.b}</td>
                          <td style={{ padding: "12px 16px", textAlign: "center" }}>
                            <span
                              style={{
                                fontFamily: FONT_MONO,
                                fontSize: "11px",
                                fontWeight: 600,
                                padding: "3px 8px",
                                borderRadius: "4px",
                                backgroundColor: d.abs_delta > 15 ? "#fee2e2" : d.abs_delta > 5 ? "#fef9c3" : "#d1fae5",
                                color: d.abs_delta > 15 ? "#7f1d1d" : d.abs_delta > 5 ? "#713f12" : "#065f46",
                              }}
                            >
                              {d.abs_delta}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState>No comparable dimensions (coverage &lt; 0.60 on both sides).</EmptyState>
              )}

              {result.excluded_dimensions.length > 0 && (
                <p style={{ fontSize: "12px", color: C.faint }}>
                  Excluded (insufficient coverage): {result.excluded_dimensions.join(", ")}
                </p>
              )}

              <button
                onClick={exportReport}
                className="mt-4 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
                style={{ backgroundColor: C.white, color: C.lavender, border: `1px solid ${C.lavenderMuted}` }}
              >
                Export comparison JSON
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
