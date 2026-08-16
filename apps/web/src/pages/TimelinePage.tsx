import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSnapshotId } from "../hooks/useJob";
import { formatDate, provenanceColor } from "../lib/format";
import { ErrorState, LoadingState } from "../components/StateViews";
import type { TimelineEvent } from "../lib/types";

export function TimelinePage() {
  const { id } = useParams<{ id: string }>();
  const { snapshotId } = useSnapshotId(id);
  const [filter, setFilter] = useState("");
  const {
    data: events,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["timeline", snapshotId],
    queryFn: () => api.timeline(snapshotId!),
    enabled: !!snapshotId,
  });
  const [selected, setSelected] = useState<TimelineEvent | null>(null);

  if (isLoading && !events) return <LoadingState />;
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />;
  if (!events || events.length === 0) return <p className="muted">No timeline yet. Run an analysis first.</p>;

  const types = [...new Set(events.map((e) => e.type))];
  const filtered = filter ? events.filter((e) => e.type === filter) : events;

  return (
    <div>
      <h1 className="mb">Timeline</h1>
      <div className="row mb">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 240 }}>
          <option value="">All event types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div className="two-col">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {filtered.map((e) => (
            <button
              key={e.id}
              className="secondary"
              style={{ textAlign: "left", padding: 12 }}
              onClick={() => setSelected(e)}
            >
              <div className="row between wrap">
                <strong style={{ fontSize: 14 }}>{e.title}</strong>
                <span className="badge" style={{ background: "var(--bg-hover)" }}>
                  {formatDate(e.occurred_at)}
                </span>
              </div>
              <div className="small muted mt">{e.summary}</div>
              <div className="row mt">
                <span className="badge accent">{e.type}</span>
                <span className="badge" style={{ background: "var(--bg-hover)" }}>
                  {e.provenance}
                </span>
                {e.components.map((c) => (
                  <span key={c} className="badge" style={{ background: "var(--bg-hover)" }}>
                    {c}
                  </span>
                ))}
              </div>
            </button>
          ))}
          {filtered.length === 0 && <p className="muted">No events match this filter.</p>}
        </div>

        <div>
          {selected && (
            <div className="card">
              <h3 className="mb">{selected.title}</h3>
              <div className="small muted mb">
                <span style={{ color: provenanceColor(selected.provenance) }}>{selected.provenance}</span>
                {" · "}
                {formatDate(selected.occurred_at)}
              </div>
              <p>{selected.summary}</p>
              <h4>Evidence</h4>
              <ul className="small">
                {(selected.artifact_ids ?? []).slice(0, 20).map((a) => (
                  <li key={a} className="muted">
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}