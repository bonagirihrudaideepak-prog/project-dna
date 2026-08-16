import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { DIMENSION_LABELS } from "../lib/format";
import type { Snapshot } from "../lib/types";

export function ComparePage() {
  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [pa, setPa] = useState("");
  const [pb, setPb] = useState("");
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [snapshotsA, setSnapshotsA] = useState<Snapshot[]>([]);
  const [snapshotsB, setSnapshotsB] = useState<Snapshot[]>([]);

  async function loadSnapshots(pid: string, which: "A" | "B") {
    if (!pid) return;
    const snaps = await api.snapshots(pid);
    const completed = snaps.filter((s) => s.status === "COMPLETED");
    if (which === "A") {
      setSnapshotsA(completed);
      setPa(completed[0]?.id ?? "");
    } else {
      setSnapshotsB(completed);
      setPb(completed[0]?.id ?? "");
    }
  }

  async function runCompare() {
    try {
      const res = await api.compare(pa, pb);
      setResult(res as Record<string, any>);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h1 className="mb">Compare projects</h1>
      <p className="muted mb">
        Uses dimensions where both snapshots have sufficient coverage. Similarity is descriptive — not a
        quality ranking.
      </p>

      <div className="grid grid-2">
        <div className="card">
          <h3 className="mb">Project A</h3>
          <select value={snapshotsA.length ? "" : ""} onChange={(e) => loadSnapshots(e.target.value, "A")}>
            <option value="">Choose project…</option>
            {(projects ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
          {snapshotsA.length > 0 && (
            <select value={pa} onChange={(e) => setPa(e.target.value)}>
              {snapshotsA.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.commit_sha.slice(0, 10)} · {new Date(s.captured_at!).toLocaleDateString()}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="card">
          <h3 className="mb">Project B</h3>
          <select onChange={(e) => loadSnapshots(e.target.value, "B")}>
            <option value="">Choose project…</option>
            {(projects ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
          {snapshotsB.length > 0 && (
            <select value={pb} onChange={(e) => setPb(e.target.value)}>
              {snapshotsB.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.commit_sha.slice(0, 10)} · {new Date(s.captured_at!).toLocaleDateString()}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="mt">
        <button disabled={!pa || !pb} onClick={runCompare}>
          Compare
        </button>
      </div>

      {error && <div className="card mt"><span className="badge bad">Error</span> {error}</div>}

      {result && (
        <div className="card mt">
          <h3 className="mb">Similarity: {result.similarity ?? "n/a"} / 100</h3>
          {result.warning && (
            <p className="small" style={{ color: "var(--yellow)" }}>
              ⚠ {result.warning}
            </p>
          )}
          <p className="small muted">
            {result.snapshot_a.project} ↔ {result.snapshot_b.project} · used{" "}
            {(result.used_dimensions ?? []).length} dimensions · similarity coverage{" "}
            {Math.round((result.similarity_coverage ?? 0) * 100)}%
          </p>
          {result.excluded_dimensions && result.excluded_dimensions.length > 0 && (
            <p className="small muted">
              Excluded (insufficient coverage): {result.excluded_dimensions.join(", ")}
            </p>
          )}
          <h4 className="mt mb">Per-dimension deltas</h4>
          <table>
            <thead>
              <tr>
                <th>Dimension</th>
                <th>A</th>
                <th>B</th>
                <th>Δ</th>
              </tr>
            </thead>
            <tbody>
              {(result.per_dimension ?? []).map((d: any) => (
                <tr key={d.dimension}>
                  <td>{DIMENSION_LABELS[d.dimension] || d.dimension}</td>
                  <td>{d.a}</td>
                  <td>{d.b}</td>
                  <td>{d.abs_delta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}