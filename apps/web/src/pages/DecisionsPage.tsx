import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { formatDate } from "../lib/format";
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import type { Decision } from "../lib/types";

function Field({
  label,
  id,
  value,
  onChange,
  textarea,
}: {
  label: string;
  id: string;
  value: string;
  onChange: (v: string) => void;
  textarea?: boolean;
}) {
  const inputStyle = {
    width: "100%",
    boxSizing: "border-box" as const,
    fontSize: "13px",
    border: `1px solid ${C.border}`,
    borderRadius: "8px",
    padding: "8px 12px",
    color: C.ink,
    backgroundColor: C.white,
    outline: "none",
    marginBottom: "10px",
  };
  return (
    <div>
      <label htmlFor={id} style={{ fontSize: "11px", fontWeight: 600, color: C.muted, display: "block", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </label>
      {textarea ? (
        <textarea id={id} rows={3} value={value} onChange={(e) => onChange(e.target.value)} style={{ ...inputStyle, resize: "vertical" }} />
      ) : (
        <input id={id} value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
      )}
    </div>
  );
}

export default function DecisionsPage() {
  const qc = useQueryClient();
  const { user, projects, loading: spineLoading } = useUserAndProjects();
  const { project, projectId } = useActiveProject(projects);
  const {
    data: decisions,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.decisions(projectId),
    queryFn: () => api.decisions(projectId!),
    enabled: !!projectId,
  });
  const [selected, setSelected] = useState<Decision | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [reviewForm, setReviewForm] = useState<Record<string, string>>({});

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.createDecision(projectId!, data),
    onSuccess: () => {
      setShowForm(false);
      setForm({});
      qc.invalidateQueries({ queryKey: queryKeys.decisions(projectId) });
    },
  });
  const reviewMut = useMutation({
    mutationFn: ({ decisionId, data }: { decisionId: string; data: Record<string, unknown> }) =>
      api.addOutcomeReview(decisionId, data),
    onSuccess: (updated) => {
      setSelected(updated);
      setReviewForm({});
      qc.invalidateQueries({ queryKey: queryKeys.decisions(projectId) });
    },
  });

  if (spineLoading || isLoading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader
        title="Decisions & Experiments"
        subtitle={`Architectural decisions with alternatives and outcomes${project ? ` — ${project.full_name}` : ""}`}
      />

      {!user || projects.length === 0 ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in
          </Link>{" "}
          and run an analysis to record decisions.
        </EmptyState>
      ) : !projectId ? null : (
        <>
          <div className="flex items-center justify-between mb-5">
            <span style={{ fontFamily: FONT_MONO, fontSize: "12px", color: C.faint }}>
              {(decisions ?? []).length} decision record(s)
            </span>
            <button
              onClick={() => setShowForm(!showForm)}
              className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
              style={{ backgroundColor: showForm ? C.white : C.lavender, color: showForm ? C.lavender : C.white, border: `1px solid ${showForm ? C.lavenderMuted : "none"}` }}
            >
              {showForm ? "Cancel" : "+ New decision"}
            </button>
          </div>

          {createMut.isError && (
            <ErrorState message={(createMut.error as Error).message} />
          )}

          {/* New decision form */}
          {showForm && (
            <div className="rounded-xl p-5 mb-6" style={panelStyle}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink, marginBottom: "12px" }}>New decision record</h3>
              <Field label="Title" id="decision-title" value={form.title ?? ""} onChange={(v) => setForm({ ...form, title: v })} />
              <Field label="Context / problem" id="decision-context" value={form.context ?? ""} onChange={(v) => setForm({ ...form, context: v })} textarea />
              <Field label="Decision" id="decision-text" value={form.decision_text ?? ""} onChange={(v) => setForm({ ...form, decision_text: v })} textarea />
              <Field label="Reason" id="decision-reason" value={form.reason ?? ""} onChange={(v) => setForm({ ...form, reason: v })} textarea />
              <button
                disabled={!form.title || createMut.isPending}
                onClick={() =>
                  createMut.mutate({
                    title: form.title,
                    context: form.context,
                    decision_text: form.decision_text,
                    reason: form.reason,
                    status: "accepted",
                  })
                }
                className="px-4 py-2 rounded-lg text-sm font-semibold cursor-pointer"
                style={{
                  backgroundColor: !form.title ? C.lavenderMuted : C.lavender,
                  color: C.white,
                  border: "none",
                  cursor: !form.title || createMut.isPending ? "not-allowed" : "pointer",
                }}
              >
                Save decision
              </button>
            </div>
          )}

          {/* Decision cards */}
          {(decisions ?? []).length === 0 ? (
            <EmptyState>No decisions recorded yet — document your first architectural call above.</EmptyState>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {(decisions ?? []).map((d) => {
                const open = selected?.id === d.id;
                return (
                  <div key={d.id} className="rounded-xl p-5 md:col-span-1" style={{ ...panelStyle, boxShadow: open ? "0 4px 16px rgba(99,102,241,0.08)" : undefined, borderColor: open ? C.lavenderMuted : C.border }}>
                    <button className="w-full text-left cursor-pointer" style={{ background: "none", border: "none", padding: 0 }} onClick={() => setSelected(open ? null : d)}>
                      <div className="flex items-start gap-3">
                        <div className="rounded-lg flex items-center justify-center flex-shrink-0" style={{ width: "36px", height: "36px", backgroundColor: "#d1fae5" }}>
                          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <path d="M2 8l4 4 8-8" stroke="#065f46" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: 600,
                                textTransform: "uppercase",
                                letterSpacing: "0.04em",
                                color: "#065f46",
                                backgroundColor: "#d1fae5",
                                padding: "1px 6px",
                                borderRadius: "4px",
                              }}
                            >
                              Decision
                            </span>
                            <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>{formatDate(d.decided_at)}</span>
                            <span style={{ fontSize: "10px", fontWeight: 500, color: C.lavender, backgroundColor: C.lavenderSoft, padding: "1px 6px", borderRadius: "4px" }}>
                              {d.status}
                            </span>
                          </div>
                          <h3 style={{ fontSize: "13px", fontWeight: 600, color: C.ink, marginBottom: "4px" }}>{d.title}</h3>
                          <p className="truncate" style={{ fontSize: "12px", color: C.muted, marginBottom: 0 }}>
                            {d.decision_text ?? d.context ?? "—"}
                          </p>
                          <div style={{ fontSize: "11px", color: C.faint, marginTop: "6px" }}>
                            {d.alternatives.length} alternative(s) · {d.outcome_reviews.length} review(s)
                          </div>
                        </div>
                      </div>
                    </button>

                    {/* Expanded detail */}
                    {open && (
                      <div className="mt-4 pt-4" style={{ borderTop: `1px solid ${C.borderLight}` }}>
                        {[
                          ["Context", d.context],
                          ["Decision", d.decision_text],
                          ["Reason", d.reason],
                        ].map(([h, body]) =>
                          body ? (
                            <div key={h as string} className="mb-3">
                              <div style={{ fontSize: "10px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "2px" }}>{h}</div>
                              <p style={{ fontSize: "12px", color: C.body, lineHeight: 1.6, marginBottom: 0 }}>{body}</p>
                            </div>
                          ) : null
                        )}

                        <div style={{ fontSize: "10px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Alternatives</div>
                        {d.alternatives.length === 0 ? (
                          <p style={{ fontSize: "12px", color: C.faint }}>No alternatives recorded.</p>
                        ) : (
                          d.alternatives.map((a) => (
                            <div key={a.id} className="rounded-lg p-3 mb-2" style={{ backgroundColor: C.pageBg }}>
                              <strong style={{ fontSize: "12px", color: C.ink }}>{a.name}</strong>
                              {a.rejection_reason && <div style={{ fontSize: "11px", color: C.muted }}>Rejected: {a.rejection_reason}</div>}
                              {a.advantages && <div style={{ fontSize: "11px", color: C.muted }}>Pros: {a.advantages}</div>}
                              {a.disadvantages && <div style={{ fontSize: "11px", color: C.muted }}>Cons: {a.disadvantages}</div>}
                            </div>
                          ))
                        )}

                        <div className="mt-3" style={{ fontSize: "10px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
                          Outcome reviews
                        </div>
                        {d.outcome_reviews.map((r) => (
                          <div key={r.id} className="rounded-lg p-3 mb-2 flex items-start gap-3" style={{ backgroundColor: C.pageBg }}>
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: 600,
                                padding: "2px 7px",
                                borderRadius: "4px",
                                backgroundColor: r.verdict === "positive" ? "#d1fae5" : r.verdict === "negative" ? "#fee2e2" : "#f1f5f9",
                                color: r.verdict === "positive" ? "#065f46" : r.verdict === "negative" ? "#7f1d1d" : C.muted,
                                textTransform: "capitalize",
                                flexShrink: 0,
                              }}
                            >
                              {r.verdict}
                            </span>
                            <div className="min-w-0">
                              {r.actual_impact && <div style={{ fontSize: "12px", color: C.body }}>{r.actual_impact}</div>}
                              {r.evidence && <div style={{ fontSize: "11px", color: C.muted }}>Evidence: {r.evidence}</div>}
                            </div>
                            <span style={{ marginLeft: "auto", fontFamily: FONT_MONO, fontSize: "10px", color: C.faint, flexShrink: 0 }}>
                              {formatDate(r.reviewed_at)}
                            </span>
                          </div>
                        ))}

                        {/* Add outcome review */}
                        <div className="mt-3 rounded-lg p-3" style={{ backgroundColor: C.pageBg }}>
                          <div style={{ fontSize: "11px", fontWeight: 600, color: C.muted, marginBottom: "8px" }}>Add outcome review</div>
                          <select
                            aria-label="Review verdict"
                            value={reviewForm.verdict ?? "neutral"}
                            onChange={(e) => setReviewForm({ ...reviewForm, verdict: e.target.value })}
                            style={{
                              fontFamily: FONT_MONO,
                              fontSize: "12px",
                              border: `1px solid ${C.border}`,
                              borderRadius: "6px",
                              padding: "6px 10px",
                              marginRight: "8px",
                              marginBottom: "8px",
                              backgroundColor: C.white,
                            }}
                          >
                            <option value="positive">Positive</option>
                            <option value="neutral">Neutral</option>
                            <option value="negative">Negative</option>
                            <option value="mixed">Mixed</option>
                          </select>
                          <input
                            placeholder="Actual impact…"
                            value={reviewForm.actual_impact ?? ""}
                            onChange={(e) => setReviewForm({ ...reviewForm, actual_impact: e.target.value })}
                            style={{ width: "100%", boxSizing: "border-box", fontSize: "12px", border: `1px solid ${C.border}`, borderRadius: "6px", padding: "6px 10px", marginBottom: "6px", outline: "none" }}
                          />
                          <input
                            placeholder="Evidence (optional)…"
                            value={reviewForm.evidence ?? ""}
                            onChange={(e) => setReviewForm({ ...reviewForm, evidence: e.target.value })}
                            style={{ width: "100%", boxSizing: "border-box", fontSize: "12px", border: `1px solid ${C.border}`, borderRadius: "6px", padding: "6px 10px", marginBottom: "8px", outline: "none" }}
                          />
                          <button
                            onClick={() =>
                              reviewMut.mutate({
                                decisionId: d.id,
                                data: {
                                  reviewed_at: new Date().toISOString(),
                                  verdict: reviewForm.verdict ?? "neutral",
                                  actual_impact: reviewForm.actual_impact,
                                  evidence: reviewForm.evidence,
                                },
                              })
                            }
                            disabled={reviewMut.isPending}
                            className="text-xs font-semibold cursor-pointer"
                            style={{ background: "none", border: "none", color: C.lavender, padding: 0 }}
                          >
                            + Add review
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          {isError && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}
        </>
      )}
    </div>
  );
}
