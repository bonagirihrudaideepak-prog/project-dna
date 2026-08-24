import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { formatDate } from "../lib/format";
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import type { Experiment } from "../lib/types";

/** Maps the Experiment.decision enum onto visual outcome buckets. */
const OUTCOME_CFG: Record<string, { color: string; bg: string; label: string }> = {
  keep: { color: "#065f46", bg: "#d1fae5", label: "Kept" },
  modify: { color: "#713f12", bg: "#fef9c3", label: "Modified" },
  remove: { color: "#7f1d1d", bg: "#fee2e2", label: "Rolled back" },
  pause: { color: "#713f12", bg: "#fef9c3", label: "Paused" },
  inconclusive: { color: C.muted, bg: C.borderLight, label: "Inconclusive" },
};

export default function ExperimentsPage() {
  const qc = useQueryClient();
  const { user, projects, loading: spineLoading } = useUserAndProjects();
  const { project, projectId } = useActiveProject(projects);
  const {
    data: experiments,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.experiments(projectId),
    queryFn: () => api.experiments(projectId!),
    enabled: !!projectId,
  });
  const [form, setForm] = useState<Record<string, string>>({});
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.createExperiment(projectId!, data),
    onSuccess: () => {
      setShowForm(false);
      setForm({});
      qc.invalidateQueries({ queryKey: queryKeys.experiments(projectId) });
    },
  });

  const all = useMemo(() => experiments ?? [], [experiments]);
  const sorted = useMemo(
    () => [...all].sort((a, b) => (b.evaluated_at ?? "").localeCompare(a.evaluated_at ?? "")),
    [all]
  );
  const outcomes = ["keep", "modify", "remove", "pause", "inconclusive"] as const;
  const presentOutcomes = outcomes.filter((o) => all.some((e) => e.decision === o));
  const filtered =
    filter === "all" ? sorted : sorted.filter((e) => e.decision === filter);

  if (spineLoading || isLoading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader
        title="Experiments"
        subtitle={`Technical experiments reconstructed and archived${project ? ` — ${project.full_name}` : ""}`}
      />

      {!user || projects.length === 0 ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in
          </Link>{" "}
          and run an analysis to archive experiments.
        </EmptyState>
      ) : !projectId ? null : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {presentOutcomes.map((o) => {
              const cfg = OUTCOME_CFG[o];
              return (
                <div key={o} className="rounded-xl p-4" style={panelStyle}>
                  <div style={{ fontSize: "11px", color: C.faint, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                    {cfg.label}
                  </div>
                  <div style={{ fontFamily: FONT_MONO, fontSize: "28px", fontWeight: 700, color: cfg.color, lineHeight: 1 }}>
                    {all.filter((e) => e.decision === o).length}
                  </div>
                </div>
              );
            })}
            <div className="rounded-xl p-4 col-span-2 md:col-span-1 flex flex-col justify-between" style={{ background: "linear-gradient(135deg, #ede9f2 0%, #fce7f3 100%)", border: `1px solid ${C.lavenderMuted}` }}>
              <div style={{ fontSize: "11px", color: C.muted, fontWeight: 500 }}>TOTAL</div>
              <button
                onClick={() => setShowForm(!showForm)}
                className="text-left cursor-pointer"
                style={{ fontFamily: FONT_MONO, fontSize: "20px", fontWeight: 700, color: C.lavender, background: "none", border: "none", padding: 0 }}
              >
                {showForm ? "Cancel ×" : `+ Record (${all.length})`}
              </button>
            </div>
          </div>

          {/* Archive form */}
          {showForm && (
            <div className="rounded-xl p-5 mb-6" style={panelStyle}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink, marginBottom: "12px" }}>Archive an experiment</h3>
              <input placeholder="Title" value={form.title ?? ""} onChange={(e) => setForm({ ...form, title: e.target.value })} style={{ width: "100%", boxSizing: "border-box", fontSize: "13px", border: `1px solid ${C.border}`, borderRadius: "8px", padding: "8px 12px", marginBottom: "10px", outline: "none" }} />
              <textarea placeholder="Hypothesis…" rows={2} value={form.hypothesis ?? ""} onChange={(e) => setForm({ ...form, hypothesis: e.target.value })} style={{ width: "100%", boxSizing: "border-box", fontSize: "13px", border: `1px solid ${C.border}`, borderRadius: "8px", padding: "8px 12px", marginBottom: "10px", outline: "none", resize: "vertical" }} />
              <textarea placeholder="Result / what happened…" rows={2} value={form.result ?? ""} onChange={(e) => setForm({ ...form, result: e.target.value })} style={{ width: "100%", boxSizing: "border-box", fontSize: "13px", border: `1px solid ${C.border}`, borderRadius: "8px", padding: "8px 12px", marginBottom: "10px", outline: "none", resize: "vertical" }} />
              <textarea placeholder="Lesson learned…" rows={2} value={form.reason ?? ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} style={{ width: "100%", boxSizing: "border-box", fontSize: "13px", border: `1px solid ${C.border}`, borderRadius: "8px", padding: "8px 12px", marginBottom: "10px", outline: "none", resize: "vertical" }} />
              <select
                aria-label="Outcome decision"
                value={form.decision ?? "remove"}
                onChange={(e) => setForm({ ...form, decision: e.target.value })}
                style={{ fontFamily: FONT_MONO, fontSize: "12px", border: `1px solid ${C.border}`, borderRadius: "6px", padding: "6px 10px", marginRight: "10px", backgroundColor: C.white }}
              >
                {outcomes.map((o) => (
                  <option key={o} value={o}>
                    {OUTCOME_CFG[o].label}
                  </option>
                ))}
              </select>
              <button
                disabled={!form.title || createMut.isPending}
                onClick={() =>
                  createMut.mutate({
                    title: form.title,
                    hypothesis: form.hypothesis,
                    result: form.result,
                    decision: form.decision ?? "remove",
                    reason: form.reason,
                    evaluated_at: new Date().toISOString(),
                  })
                }
                className="px-4 py-2 rounded-lg text-sm font-semibold"
                style={{
                  backgroundColor: !form.title ? C.lavenderMuted : C.lavender,
                  color: C.white,
                  border: "none",
                  cursor: !form.title || createMut.isPending ? "not-allowed" : "pointer",
                }}
              >
                Save experiment
              </button>
            </div>
          )}

          {/* Filters */}
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            <button
              onClick={() => setFilter("all")}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer"
              style={{
                backgroundColor: filter === "all" ? C.lavenderSoft : C.pageBg,
                color: filter === "all" ? C.lavender : C.muted,
                border: `1px solid ${filter === "all" ? C.lavenderMuted : C.border}`,
              }}
            >
              All ({all.length})
            </button>
            {presentOutcomes.map((o) => {
              const cfg = OUTCOME_CFG[o];
              const active = filter === o;
              return (
                <button
                  key={o}
                  onClick={() => setFilter(o)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer"
                  style={{
                    backgroundColor: active ? cfg.bg : C.pageBg,
                    color: active ? cfg.color : C.muted,
                    border: `1px solid ${active ? cfg.color + "55" : C.border}`,
                  }}
                >
                  {cfg.label}
                </button>
              );
            })}
          </div>

          {isError && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}

          {/* Experiment cards */}
          {filtered.length === 0 ? (
            <EmptyState>No experiments archived yet. Preserve failed ideas and their lessons here.</EmptyState>
          ) : (
            <div className="space-y-3">
              {filtered.map((e) => {
                const cfg = OUTCOME_CFG[e.decision] ?? OUTCOME_CFG.inconclusive;
                return (
                  <div key={e.id} className="rounded-xl p-5" style={panelStyle}>
                    <div className="flex items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "4px", backgroundColor: cfg.bg, color: cfg.color }}>
                            {cfg.label}
                          </span>
                          <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>
                            {formatDate(e.start_at)} – {formatDate(e.evaluated_at)}
                          </span>
                        </div>
                        <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink, marginBottom: "6px" }}>{e.title}</h3>
                        {e.hypothesis && <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.65 }}>{e.hypothesis}</p>}
                        {e.result && (
                          <p style={{ fontSize: "12px", color: C.body, lineHeight: 1.65 }}>
                            <strong>Result:</strong> {e.result}
                          </p>
                        )}
                        {e.reason && (
                          <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.65 }}>
                            <strong>Lesson:</strong> {e.reason}
                          </p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0 hidden sm:block">
                        <div style={{ fontSize: "10px", color: C.faint, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>
                          Outcome
                        </div>
                        <div style={{ fontSize: "13px", fontWeight: 600, color: cfg.color }}>{cfg.label}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
