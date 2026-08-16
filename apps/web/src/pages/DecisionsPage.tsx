import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import { ErrorState, LoadingState } from "../components/StateViews";
import type { Decision } from "../lib/types";

export function DecisionsPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const {
    data: decisions,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["decisions", id],
    queryFn: () => api.decisions(id!),
    enabled: !!id,
  });
  const [selected, setSelected] = useState<Decision | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [reviewForm, setReviewForm] = useState<Record<string, string>>({});

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.createDecision(id!, data),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ["decisions", id] });
    },
  });
  const reviewMut = useMutation({
    mutationFn: ({ decisionId, data }: { decisionId: string; data: Record<string, unknown> }) =>
      api.addOutcomeReview(decisionId, data),
    onSuccess: (updated) => {
      setSelected(updated);
      qc.invalidateQueries({ queryKey: ["decisions", id] });
    },
  });

  return (
    <div>
      <div className="row between mb">
        <h1>Decision Archaeology</h1>
        <button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "+ New decision"}</button>
      </div>

      {showForm && (
        <div className="card mb-lg">
          <h3 className="mb">New decision record</h3>
          <label htmlFor="decision-title">Title</label>
          <input
            id="decision-title"
            value={form.title || ""}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <label htmlFor="decision-context">Context / problem</label>
          <textarea
            id="decision-context"
            rows={3}
            value={form.context || ""}
            onChange={(e) => setForm({ ...form, context: e.target.value })}
          />
          <label htmlFor="decision-text">Decision</label>
          <textarea
            id="decision-text"
            rows={2}
            value={form.decision_text || ""}
            onChange={(e) => setForm({ ...form, decision_text: e.target.value })}
          />
          <label htmlFor="decision-reason">Reason</label>
          <textarea
            id="decision-reason"
            rows={2}
            value={form.reason || ""}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
          />
          <div className="mt">
            <button
              disabled={!form.title}
              onClick={() =>
                createMut.mutate({
                  title: form.title,
                  context: form.context,
                  decision_text: form.decision_text,
                  reason: form.reason,
                  status: "accepted",
                })
              }
            >
              Save
            </button>
          </div>
        </div>
      )}

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {isLoading && !decisions ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          ) : (
            <>
              {(decisions ?? []).map((d) => (
                <button key={d.id} className="secondary" style={{ textAlign: "left", padding: 12 }} onClick={() => setSelected(d)}>
                  <div className="row between wrap">
                    <strong>{d.title}</strong>
                    <span className="badge accent">{d.status}</span>
                  </div>
                  <div className="small muted mt">
                    {formatDate(d.decided_at)} · {d.alternatives.length} alternatives ·{" "}
                    {d.outcome_reviews.length} review(s)
                  </div>
                </button>
              ))}
              {(decisions ?? []).length === 0 && <p className="muted">No decisions recorded yet.</p>}
            </>
          )}
        </div>

        <div>
          {selected && (
            <div className="card">
              <h3 className="mb">{selected.title}</h3>
              <p className="small muted mb">
                {formatDate(selected.decided_at)} · status <strong>{selected.status}</strong> · provenance{" "}
                {selected.provenance}
              </p>
              <h4>Context</h4>
              <p className="small">{selected.context}</p>
              <h4>Decision</h4>
              <p className="small">{selected.decision_text}</p>
              <h4>Reason</h4>
              <p className="small">{selected.reason}</p>

              <h4 className="mb">Alternatives</h4>
              {selected.alternatives.map((a) => (
                <div key={a.id} className="card" style={{ padding: 12, marginBottom: 8 }}>
                  <strong className="small">{a.name}</strong>
                  {a.rejection_reason && <div className="small muted">Rejected: {a.rejection_reason}</div>}
                </div>
              ))}
              {selected.alternatives.length === 0 && (
                <p className="small muted">No alternatives recorded.</p>
              )}

              <h4 className="mb">Outcome reviews</h4>
              {selected.outcome_reviews.map((r) => (
                <div key={r.id} className="card" style={{ padding: 12, marginBottom: 8 }}>
                  <div className="row between">
                    <span className="badge ok">{r.verdict}</span>
                    <span className="small muted">{formatDate(r.reviewed_at)}</span>
                  </div>
                  <p className="small mt">{r.actual_impact}</p>
                  {r.evidence && <p className="small muted">Evidence: {r.evidence}</p>}
                </div>
              ))}

              <h4 className="mb">Add outcome review</h4>
              <label htmlFor="review-verdict">Verdict</label>
              <select id="review-verdict" value={reviewForm.verdict || "neutral"} onChange={(e) => setReviewForm({ ...reviewForm, verdict: e.target.value })}>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
                <option value="mixed">Mixed</option>
              </select>
              <label htmlFor="review-impact">Actual impact</label>
              <textarea id="review-impact" rows={2} value={reviewForm.actual_impact || ""} onChange={(e) => setReviewForm({ ...reviewForm, actual_impact: e.target.value })} />
              <label htmlFor="review-evidence">Evidence</label>
              <textarea id="review-evidence" rows={2} value={reviewForm.evidence || ""} onChange={(e) => setReviewForm({ ...reviewForm, evidence: e.target.value })} />
              <div className="mt">
                <button
                  onClick={() =>
                    reviewMut.mutate({
                      decisionId: selected.id,
                      data: {
                        reviewed_at: new Date().toISOString(),
                        verdict: reviewForm.verdict || "neutral",
                        actual_impact: reviewForm.actual_impact,
                        evidence: reviewForm.evidence,
                      },
                    })
                  }
                >
                  Add review
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}