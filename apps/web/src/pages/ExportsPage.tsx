import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSnapshotId } from "../hooks/useJob";

export function ExportsPage() {
  const { id } = useParams<{ id: string }>();
  const { snapshotId, loading } = useSnapshotId(id);
  const { data: project } = useQuery({ queryKey: ["project", id], queryFn: () => api.project(id!) });
  const [json, setJson] = useState<string | null>(null);
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (loading) return <p className="muted">Loading…</p>;
  if (!snapshotId) return <p className="muted">No completed snapshot to export.</p>;

  const sid: string = snapshotId;

  async function downloadJson() {
    try {
      const res = await api.exportJson(sid);
      const text = typeof res === "string" ? res : JSON.stringify(res, null, 2);
      setJson(text);
      const blob = new Blob([text], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.full_name?.replace("/", "-")}-dna.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(String(e));
    }
  }

  async function downloadHtml() {
    try {
      const text = await api.exportHtml(sid);
      setHtml(text);
      const blob = new Blob([text], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.full_name?.replace("/", "-")}-dna.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h1 className="mb">Exports</h1>
      {error && <div className="card mt"><span className="badge bad">Error</span> {error}</div>}
      <div className="grid grid-2">
        <div className="card">
          <h3>JSON export</h3>
          <p className="muted small">
            Full structured snapshot: project, DNA scores, timeline, decisions, and experiments.
          </p>
          <button onClick={downloadJson}>Download JSON</button>
        </div>
        <div className="card">
          <h3>Print-friendly report</h3>
          <p className="muted small">A printable HTML report for your viva or documentation.</p>
          <button onClick={downloadHtml}>Download HTML</button>
        </div>
      </div>
      {json && (
        <div className="card mt">
          <h4>JSON preview</h4>
          <pre className="code">{json.slice(0, 3000)}…</pre>
        </div>
      )}
      {html && (
        <div className="card mt">
          <h4>HTML preview</h4>
          <iframe title="HTML export preview" srcDoc={html} style={{ width: "100%", height: 480, border: "1px solid var(--border)", borderRadius: 8, background: "#fff" }} />
        </div>
      )}
    </div>
  );
}