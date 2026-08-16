import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import cytoscape from "cytoscape";
import { api } from "../lib/api";
import { useSnapshotId } from "../hooks/useJob";
import { ErrorState, LoadingState } from "../components/StateViews";

const NODE_COLORS: Record<string, string> = {
  project: "#58a6ff",
  snapshot: "#8b949e",
  event: "#3fb950",
  decision: "#bc8cff",
  experiment: "#d29922",
  component: "#39c5cf",
  outcome: "#f85149",
};

export function GraphPage() {
  const { id } = useParams<{ id: string }>();
  const { snapshotId } = useSnapshotId(id);
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["graph", snapshotId],
    queryFn: () => api.graph(snapshotId!),
    enabled: !!snapshotId,
  });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!data || !containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...(data.nodes ?? []).map((n) => ({
          data: {
            id: n.key,
            label: n.label,
            type: n.node_type,
          },
        })),
        ...(data.edges ?? []).map((e, i) => ({
          data: {
            id: `e${i}-${e.source}-${e.target}`,
            source: e.source,
            target: e.target,
            label: e.edge_type,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele: any) => NODE_COLORS[ele.data("type")] || "#8b949e",
            label: "data(label)",
            color: "#e6edf3",
            "font-size": 10,
            "text-wrap": "wrap",
            "text-max-width": "120px",
            width: 36,
            height: 36,
            "overlay-opacity": 0,
          },
        },
        {
          selector: "edge",
          style: {
            "line-color": "#30363d",
            "target-arrow-color": "#30363d",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            color: "#8b949e",
          },
        },
      ],
      layout: { name: "cose", animate: true, padding: 30 },
    });
    return () => {
      cy.destroy();
    };
  }, [data]);

  return (
    <div>
      <h1 className="mb">Evolution Graph</h1>
      <p className="muted small mb">
        Every node and edge carries provenance: observed, rule-derived, user, or suggested. Bounded to one
        hop by default.
      </p>
      {isLoading && !data ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
      ) : data && (data.nodes ?? []).length === 0 ? (
        <p className="muted">No graph data yet.</p>
      ) : (
        <div ref={containerRef} style={{ height: 560, border: "1px solid var(--border)", borderRadius: 10, background: "#0d1117" }} />
      )}
      <div className="mt">
        {Object.entries(NODE_COLORS).map(([t, c]) => (
          <span key={t} className="badge" style={{ background: "var(--bg-hover)" }}>
            <span style={{ display: "inline-block", width: 10, height: 10, background: c, borderRadius: 3, marginRight: 6 }} />
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}