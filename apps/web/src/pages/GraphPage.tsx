import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import cytoscape, { type Core } from "cytoscape";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { useSnapshotId } from "../hooks/useJob";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { C, FONT_MONO, panelStyle } from "../lib/ui";

/** Node palette per node_type — mapped onto the design's lavender/green/amber family. */
const TYPE_STYLE: Record<string, { color: string; bg: string }> = {
  release: { color: C.lavender, bg: C.lavenderSoft },
  decision: { color: "#10b981", bg: "#d1fae5" },
  experiment: { color: "#f59e0b", bg: "#fef9c3" },
  component: { color: "#0ea5e9", bg: "#e0f2fe" },
  event: { color: "#64748b", bg: "#f1f5f9" },
  snapshot: { color: "#94a3b8", bg: "#f8fafc" },
  outcome: { color: "#ef4444", bg: "#fee2e2" },
};

function styleFor(type: string) {
  return TYPE_STYLE[type] ?? { color: "#64748b", bg: "#f1f5f9" };
}

export default function GraphPage() {
  const { user, projects, loading: spineLoading } = useUserAndProjects();
  const { project, projectId } = useActiveProject(projects);
  const { snapshotId } = useSnapshotId(projectId);
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.graph(snapshotId),
    queryFn: () => api.graph(snapshotId!),
    enabled: !!snapshotId,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [hovered, setHovered] = useState<{ label: string; type: string; degree: number } | null>(null);

  const nodeTypes = useMemo(() => {
    const counts = new Map<string, number>();
    for (const n of data?.nodes ?? []) counts.set(n.node_type, (counts.get(n.node_type) ?? 0) + 1);
    return Array.from(counts.entries());
  }, [data]);

  useEffect(() => {
    if (!data || !containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...(data.nodes ?? []).map((n) => ({
          data: { id: n.key, label: n.label, type: n.node_type },
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
            "background-color": (ele: unknown) => styleFor((ele as { data: (k: string) => string }).data("type")).color,
            "background-opacity": 0.9,
            label: "data(label)",
            color: C.body,
            "font-size": 10,
            "font-family": "DM Sans",
            "text-wrap": "wrap",
            "text-max-width": "110px",
            width: 30,
            height: 30,
            "border-width": 2,
            "border-color": "#ffffff",
            "overlay-opacity": 0,
          },
        },
        {
          selector: "edge",
          style: {
            "line-color": C.border,
            "target-arrow-color": C.border,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            color: C.faint,
            width: 1.4,
          },
        },
      ],
      layout: { name: "cose", animate: true, padding: 40 },
    });
    cyRef.current = cy;

    const onOver = (evt: { target: { isNode: () => boolean; data: (k: string) => string; degree: (includeLoops?: boolean) => number } }) => {
      if (!evt.target.isNode()) return;
      setHovered({ label: evt.target.data("label"), type: evt.target.data("type"), degree: evt.target.degree(true) });
    };
    const onOut = () => setHovered(null);
    cy.on("mouseover", "node", onOver);
    cy.on("mouseout", "node", onOut);

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [data]);

  // Type filtering
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        if (filter === "all" || n.data("type") === filter) n.removeClass("dimmed");
        else n.addClass("dimmed");
      });
    });
  }, [filter, data]);

  // Dimmed style needs to exist on the stylesheet — add via a class selector
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.style()
      .selector(".dimmed")
      .style({ opacity: 0.15 })
      .update();
  }, [data]);

  const applyZoom = (delta: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: Math.min(3, Math.max(0.2, cy.zoom() * delta)), renderedPosition: { x: (cy.width() as number) / 2, y: (cy.height() as number) / 2 } });  };

  if (spineLoading || isLoading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader
        title="Evolution Graph"
        subtitle={`Decisions, experiments, releases, and components${project ? ` — ${project.full_name}` : ""} · drag to pan, scroll to zoom`}
      />

      {!user || projects.length === 0 ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in
          </Link>{" "}
          and run an analysis to build an evolution graph.
        </EmptyState>
      ) : !snapshotId ? (
        <EmptyState>No completed analysis for this repository yet.</EmptyState>
      ) : isError ? (
        <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
      ) : (
        <>
          {/* Toolbar */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <button
              onClick={() => setFilter("all")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer"
              style={{
                backgroundColor: filter === "all" ? C.lavenderSoft : C.pageBg,
                color: filter === "all" ? C.lavender : C.muted,
                border: `1px solid ${filter === "all" ? C.lavenderMuted : C.border}`,
              }}
            >
              All ({(data?.nodes ?? []).length})
            </button>
            {nodeTypes.map(([t, count]) => {
              const s = styleFor(t);
              const active = filter === t;
              return (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer"
                  style={{
                    backgroundColor: active ? s.bg : C.pageBg,
                    color: active ? s.color : C.muted,
                    border: `1px solid ${active ? s.color + "55" : C.border}`,
                  }}
                >
                  <span style={{ width: "8px", height: "8px", borderRadius: "2px", backgroundColor: s.color, display: "inline-block" }} />
                  {t}s ({count})
                </button>
              );
            })}

            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={() => applyZoom(1 / 1.2)}
                aria-label="Zoom out"
                className="cursor-pointer"
                style={{ width: "30px", height: "30px", borderRadius: "6px", border: `1px solid ${C.border}`, backgroundColor: C.pageBg, fontSize: "16px", color: C.body }}
              >
                −
              </button>
              <button
                onClick={() => applyZoom(1.2)}
                aria-label="Zoom in"
                className="cursor-pointer"
                style={{ width: "30px", height: "30px", borderRadius: "6px", border: `1px solid ${C.border}`, backgroundColor: C.pageBg, fontSize: "16px", color: C.body }}
              >
                +
              </button>
              <button
                onClick={() => cyRef.current?.fit(undefined, 40)}
                className="px-3 rounded-lg cursor-pointer"
                style={{ height: "30px", border: `1px solid ${C.border}`, backgroundColor: C.pageBg, fontSize: "12px", color: C.body }}
              >
                Fit
              </button>
            </div>
          </div>

          {/* Canvas */}
          {(data?.nodes ?? []).length === 0 ? (
            <EmptyState>No graph data yet.</EmptyState>
          ) : (
            <div
              className="rounded-xl overflow-hidden relative"
              style={{
                ...panelStyle,
                height: "520px",
                backgroundImage: "radial-gradient(circle, #cbd5e1 1px, transparent 1px)",
                backgroundSize: "24px 24px",
              }}
            >
              <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
              <span
                className="hidden md:block"
                style={{ position: "absolute", bottom: "12px", right: "14px", fontSize: "11px", color: C.faint, pointerEvents: "none", backgroundColor: "rgba(255,255,255,0.7)", padding: "2px 8px", borderRadius: "6px" }}
              >
                Scroll to zoom · Drag to pan · Hover a node
              </span>
            </div>
          )}

          {/* Detail bar */}
          <div className="mt-3 rounded-xl px-5 py-3 flex items-center gap-4 flex-wrap min-h-12" style={panelStyle}>
            {hovered ? (
              <>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: "4px",
                    backgroundColor: styleFor(hovered.type).bg,
                    color: styleFor(hovered.type).color,
                    textTransform: "capitalize",
                  }}
                >
                  {hovered.type}
                </span>
                <span style={{ fontFamily: FONT_MONO, fontSize: "13px", fontWeight: 700, color: C.ink }}>{hovered.label}</span>
                <span style={{ marginLeft: "auto", fontSize: "12px", color: C.faint }}>{hovered.degree} connections</span>
              </>
            ) : (
              <p style={{ fontSize: "12px", color: C.faint }}>
                Every node and edge carries provenance: observed, rule-derived, user, or suggested.
              </p>
            )}
          </div>

          {/* Legend */}
          <div className="mt-3 flex items-center gap-3 flex-wrap">
            {nodeTypes.map(([t]) => {
              const s = styleFor(t);
              return (
                <span key={t} className="flex items-center gap-1.5" style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.muted }}>
                  <span style={{ display: "inline-block", width: 10, height: 10, background: s.color, borderRadius: 3 }} />
                  {t}
                </span>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
