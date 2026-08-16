import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import { ErrorState, LoadingState } from "../components/StateViews";

export function ExperimentsPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const {
    data: experiments,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["experiments", id],
    queryFn: () => api.experiments(id!),
    enabled: !!id,
  });
  const [form, setForm] = useState<Record<string, string>>({});
  const [showForm, setShowForm] = useState(false);

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.createExperiment(id!, data),
    onSuccess: () => {
      setShowForm(false);
      setForm({});
      qc.invalidateQueries({ queryKey: ["experiments", id] });
    },
  });

  return (
    <div>
      <div className="row between mb">
        <h1>Failed Experiments</h1>
        <button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "+ Record experiment"}</button>
      </div>

      {showForm && (
        <div className="card mb-lg">
          <h3 className="mb">Archive a failed experiment</h3>
          <label htmlFor="exp-title">Title</label>
          <input id="exp-title" value={form.title || ""} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <label htmlFor="exp-hypothesis">Hypothesis</label>
          <textarea id="exp-hypothesis" rows={2} value={form.hypothesis || ""} onChange={(e) => setForm({ ...form, hypothesis: e.target.value })} />
          <label htmlFor="exp-criterion">Success criterion</label>
          <textarea id="exp-criterion" rows={2} value={form.success_criterion || ""} onChange={(e) => setForm({ ...form, success_criterion: e.target.value })} />
          <label htmlFor="exp-result">Result</label>
          <textarea id="exp-result" rows={2} value={form.result || ""} onChange={(e) => setForm({ ...form, result: e.target.value })} />
          <label htmlFor="exp-decision">Decision</label>
          <select id="exp-decision" value={form.decision || "remove"} onChange={(e) => setForm({ ...form, decision: e.target.value })}>
            <option value="remove">Remove</option>
            <option value="modify">Modify</option>
            <option value="keep">Keep</option>
            <option value="pause">Pause</option>
            <option value="inconclusive">Inconclusive</option>
          </select>
          <label htmlFor="exp-reason">Reason / lessons</label>
          <textarea id="exp-reason" rows={2} value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          <div className="mt">
            <button
              disabled={!form.title}
              onClick={() =>
                createMut.mutate({
                  title: form.title,
                  hypothesis: form.hypothesis,
                  success_criterion: form.success_criterion,
                  result: form.result,
                  decision: form.decision || "remove",
                  reason: form.reason,
                  evaluated_at: new Date().toISOString(),
                })
              }
            >
              Save experiment
            </button>
          </div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isLoading && !experiments ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
        ) : (
          <>
            {(experiments ?? []).map((e) => (
              <div key={e.id} className="card">
                <div className="row between wrap">
                  <strong>{e.title}</strong>
                  <span className="badge warn">{e.decision}</span>
                </div>
                <p className="small muted mt">{e.hypothesis}</p>
                {e.result && (
                  <p className="small mt">
                    <strong>Result:</strong> {e.result}
                  </p>
                )}
                {e.reason && (
                  <p className="small muted mt">
                    <strong>Lesson:</strong> {e.reason}
                  </p>
                )}
                <div className="small muted mt">{formatDate(e.evaluated_at)}</div>
              </div>
            ))}
            {(experiments ?? []).length === 0 && (
              <p className="muted">No experiments archived yet. Preserve failed ideas here.</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}