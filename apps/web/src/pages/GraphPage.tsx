import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import cytoscape, { type Core, type NodeSingular } from "cytoscape";
import dagre from "cytoscape-dagre";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { useSnapshotId } from "../hooks/useJob";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { C, FONT_MONO, panelStyle } from "../lib/ui";

cytoscape.use(dagre);

/**
 * Visual encoding: color + shape + size per node_type.
 * - project / snapshot  → large hubs
 * - release             → star (milestones)
 * - decision            → diamond (branch points)
 * - experiment          → round-rectangle (tried things)
 * - event               → small dot (raw history)
 * - component           → hexagon (code areas)
 * - outcome             → triangle (results)
 */
const TYPE_STYLE: Record<
  string,
  { color: string; bg: string; shape: string; size: number; glyph: string }
> = {
  project:    { color: C.lavender,  bg: "#eef2ff", shape: "round-rectangle", size: 46, glyph: "◼" },
  snapshot:   { color: "#475569",   bg: "#f1f5f9", shape: "cut-rectangle",   size: 42, glyph: "◫" },
  release:    { color: C.lavender,  bg: C.lavenderSoft, shape: "star",       size: 30, glyph: "★" },
  decision:   { color: "#10b981",   bg: "#d1fae5", shape: "diamond",         size: 30, glyph: "◆" },
  experiment: { color: "#f59e0b",   bg: "#fef9c3", shape: "round-rectangle", size: 28, glyph: "▣" },
  component:  { color: "#0ea5e9",   bg: "#e0f2fe", shape: "hexagon",         size: 22, glyph: "⬡" },
  event:      { color: "#94a3b8",   bg: "#f1f5f9", shape: "ellipse",         size: 16, glyph: "●" },
  outcome:    { color: "#ef4444",   bg: "#fee2e2", shape: "triangle",        size: 22, glyph: "▲" },
};

function styleFor(type: string) {
  return (
    TYPE_STYLE[type] ?? {
      color: "#94a3b8",
      bg: "#f1f5f9",
      shape: "ellipse",
      size: 18,
      glyph: "●",
    }
  );
}

const SHORT_MAX = 20;
function shortLabel(label: string): string {
  const one = label.replace(/\s+/g, " ").trim();
  return one.length > SHORT_MAX ? `${one.slice(0, SHORT_MAX - 1)}…` : one;
}

interface InspectedNode {
  id: string;
  label: string;
  type: string;
  degree: number;
  metadata: Record<string, unknown>;
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
  const pinnedIdRef = useRef<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [inspected, setInspected] = useState<InspectedNode | null>(null);
  const [hoverName, setHoverName] = useState<string | null>(null);

  const nodeTypes = useMemo(() => {
    const counts = new Map<string, number>();
    for (const n of data?.nodes ?? []) counts.set(n.node_type, (counts.get(n.node_type) ?? 0) + 1);
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  useEffect(() => {
    if (!data || !containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...(data.nodes ?? []).map((n) => ({
          data: {
            id: n.key,
            label: n.label,
            short: shortLabel(n.label),
            type: n.node_type,
            meta: n.metadata_json ?? {},
          },
        })),
        ...(data.edges ?? []).map((e, i) => ({
          data: {
            id: `e${i}-${e.source}-${e.target}`,
            source: e.source,
            target: e.target,
            label: e.edge_type,
            provenance: e.provenance,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(short)",
            "text-valign": "bottom",
            "text-margin-y": 6,
            color: C.body,
            "font-size": 10,
            "font-family": "DM Sans",
            "text-wrap": "ellipsis",
            "text-max-width": "120px",
            width: 24,
            height: 24,
            "background-color": "#94a3b8",
            "border-width": 2,
            "border-color": "#ffffff",
            "overlay-opacity": 0,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "line-color": "#dbe2ea",
            "target-arrow-color": "#c3ccd6",
            "target-arrow-shape": "triangle",
            "curve-style": "straight",
            "arrow-scale": 0.9,
            label: "data(label)",
            "font-size": 8,
            "font-family": "DM Sans",
            color: C.faint,
            "text-background-color": "#fafbfc",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
            // Edge labels only when the edge is highlighted
            "text-opacity": 0,
          },
        },
      ],
      layout: { name: "dagre", rankDir: "LR", nodeSep: 44, rankSep: 80, animate: true, animationDuration: 300, padding: 24 } as never,
      wheelSensitivity: 0.25,
    });
    cyRef.current = cy;

    // Per-type visual encoding (shape/color/size) applied imperatively — the
    // type set is dynamic and comes from the API.
    cy.batch(() => {
      cy.nodes().forEach((n: NodeSingular) => {
        const s = styleFor(n.data("type"));
        n.style({ shape: s.shape as never, width: s.size, height: s.size, "background-color": s.color });
      });
    });

    const highlight = (n: NodeSingular) => {
      cy.elements().addClass("dimmed");
      const hood = n.closedNeighborhood();
      hood.removeClass("dimmed");
      hood.edges().addClass("lit");
    };
    const clearHighlight = () => {
      cy.elements().removeClass("dimmed lit");
    };

    const onOver = (evt: { target: NodeSingular }) => {
      if (!evt.target.isNode()) return;
      setHoverName(evt.target.data("short"));
      highlight(evt.target);
    };
    const onOut = () => {
      setHoverName(null);
      if (!pinnedIdRef.current) clearHighlight();
    };
    const onTap = (evt: { target: NodeSingular }) => {
      if (!evt.target.isNode()) return;
      const n = evt.target;
      pinnedIdRef.current = n.id();
      setInspected({
        id: n.id(),
        label: n.data("label"),
        type: n.data("type"),
        degree: n.degree(false),
        metadata: n.data("meta") ?? {},
      });
      highlight(n);
    };
    const onTapBg = () => {
      pinnedIdRef.current = null;
      setInspected(null);
      clearHighlight();
    };

    cy.on("mouseover", "node", onOver);
    cy.on("mouseout", "node", onOut);
    cy.on("tap", "node", onTap);
    cy.on("tap", evt => {
      if (evt.target === cy) onTapBg();
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Type filtering + search dimming
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const q = search.trim().toLowerCase();
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        const typeOk = filter === "all" || n.data("type") === filter;
        const searchOk =
          !q || String(n.data("label")).toLowerCase().includes(q);
        if (typeOk && searchOk) n.removeClass("filtered-out");
        else n.addClass("filtered-out");
      });
      // Hide edges whose both ends are filtered out
      cy.edges().forEach((e) => {
        const keep =
          !e.source().hasClass("filtered-out") || !e.target().hasClass("filtered-out");
        if (keep) e.removeClass("edge-hidden");
        else e.addClass("edge-hidden");
      });
    });
  }, [filter, search, data]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const styles = cy.style();
    styles.selector(".dimmed").style({ opacity: 0.12 });
    styles.selector(".filtered-out").style({ opacity: 0.06 });
    styles.selector(".edge-hidden").style({ display: "none" });
    styles.selector("edge.lit").style({
      "text-opacity": 1,
      width: 2,
      "line-color": "#a5b4fc",
      "target-arrow-color": "#a5b4fc",
    });
    styles.update();
  }, [data]);

  const applyZoom = (delta: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: Math.min(3, Math.max(0.15, cy.zoom() * delta)),
      renderedPosition: { x: (cy.width() as number) / 2, y: (cy.height() as number) / 2 },
    });
  };

  if (spineLoading || isLoading) return <LoadingState />;

  const totalNodes = (data?.nodes ?? []).length;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader
        title="Evolution Graph"
        subtitle={`How ${project ? project.full_name : "the repository"} evolved${snapshotId ? ` · snapshot ${snapshotId.slice(0, 8)}` : ""} · shapes+colors = kind, arrows show influence`}
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
      ) : totalNodes === 0 ? (
        <EmptyState>No graph data in this snapshot.</EmptyState>
      ) : (
        <>
          {/* Toolbar */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <button
              onClick={() => { setFilter("all"); setSearch(""); }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer"
              style={{
                backgroundColor: filter === "all" && !search ? C.lavenderSoft : C.pageBg,
                color: filter === "all" && !search ? C.lavender : C.muted,
                border: `1px solid ${filter === "all" && !search ? C.lavenderMuted : C.border}`,
              }}
            >
              All ({totalNodes})
            </button>
            {nodeTypes.map(([t, count]) => {
              const s = styleFor(t);
              const active = filter === t;
              return (
                <button
                  key={t}
                  onClick={() => setFilter(active ? "all" : t)}
                  title={`${t}`}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer"
                  style={{
                    backgroundColor: active ? s.bg : C.pageBg,
                    color: active ? s.color : C.muted,
                    border: `1px solid ${active ? s.color + "66" : C.border}`,
                  }}
                >
                  <span style={{ color: s.color, fontSize: "10px", lineHeight: 1 }}>{s.glyph}</span>
                  {t}
                  <span style={{ fontFamily: FONT_MONO, opacity: 0.7 }}>{count}</span>
                </button>
              );
            })}

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Find a node…"
              aria-label="Search nodes"
              style={{
                marginLeft: "auto",
                width: 200,
                boxSizing: "border-box",
                fontSize: "12px",
                border: `1px solid ${C.border}`,
                borderRadius: "8px",
                padding: "6px 10px",
                outline: "none",
                backgroundColor: C.white,
              }}
            />
            <div className="flex items-center gap-2">
              <button onClick={() => applyZoom(1 / 1.25)} aria-label="Zoom out" className="cursor-pointer" style={{ width: "30px", height: "30px", borderRadius: "6px", border: `1px solid ${C.border}`, backgroundColor: C.pageBg, fontSize: "16px", color: C.body }}>−</button>
              <button onClick={() => applyZoom(1.25)} aria-label="Zoom in" className="cursor-pointer" style={{ width: "30px", height: "30px", borderRadius: "6px", border: `1px solid ${C.border}`, backgroundColor: C.pageBg, fontSize: "16px", color: C.body }}>+</button>
              <button onClick={() => cyRef.current?.fit(undefined, 40)} className="px-3 rounded-lg cursor-pointer" style={{ height: "30px", border: `1px solid ${C.border}`, backgroundColor: C.pageBg, fontSize: "12px", color: C.body }}>Fit</button>
            </div>
          </div>

          {/* Canvas */}
          <div
            className="rounded-xl overflow-hidden relative"
            style={{
              ...panelStyle,
              height: "560px",
              backgroundImage: "radial-gradient(circle, #dde3ea 1px, transparent 1px)",
              backgroundSize: "26px 26px",
            }}
          >
            <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
            <span
              className="hidden md:block"
              style={{
                position: "absolute",
                bottom: "10px",
                right: "14px",
                fontSize: "11px",
                color: C.faint,
                pointerEvents: "none",
                backgroundColor: "rgba(255,255,255,0.75)",
                padding: "2px 8px",
                borderRadius: "6px",
              }}
            >
              Click a node to trace its story · drag to pan · scroll to zoom
            </span>
          </div>

          {/* Detail bar */}
          <div className="mt-3 rounded-xl px-5 py-3 flex items-start gap-4 min-h-14 flex-wrap" style={panelStyle}>
            {inspected ? (
              (() => {
                const s = styleFor(inspected.type);
                const metaEntries = Object.entries(inspected.metadata).filter(([, v]) => v !== null && v !== "");
                return (
                  <>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "3px 9px",
                        borderRadius: "6px",
                        backgroundColor: s.bg,
                        color: s.color,
                        textTransform: "capitalize",
                        flexShrink: 0,
                      }}
                    >
                      <span>{s.glyph}</span> {inspected.type}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div style={{ fontSize: "13px", fontWeight: 700, color: C.ink, wordBreak: "break-word" }}>
                        {inspected.label}
                      </div>
                      {metaEntries.length > 0 && (
                        <div className="flex items-center gap-3 flex-wrap mt-1">
                          {metaEntries.slice(0, 4).map(([k, v]) => (
                            <span key={k} style={{ fontSize: "11px", color: C.muted }}>
                              <span style={{ color: C.faint, textTransform: "capitalize" }}>{k.replace(/_/g, " ")}:</span>{" "}
                              <span style={{ fontFamily: FONT_MONO }}>
                                {typeof v === "object" ? JSON.stringify(v).slice(0, 40) : String(v).slice(0, 60)}
                              </span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <span style={{ marginLeft: "auto", fontSize: "12px", color: C.faint, flexShrink: 0 }}>
                      {inspected.degree} connections · click background to clear
                    </span>
                  </>
                );
              })()
            ) : hoverName ? (
              <p style={{ fontSize: "13px", fontWeight: 600, color: C.body, margin: 0 }}>
                {hoverName} <span style={{ color: C.faint, fontWeight: 400 }}>· click to inspect</span>
              </p>
            ) : (
              <p style={{ fontSize: "12px", color: C.faint, margin: 0 }}>
                Hover to spotlight connections · click a node for details · dashed-free straight arrows point at what influenced what
              </p>
            )}
          </div>

          {/* Legend */}
          <div className="mt-3 flex items-center gap-4 flex-wrap">
            {nodeTypes.map(([t]) => {
              const s = styleFor(t);
              return (
                <span key={t} className="flex items-center gap-1.5" style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.muted }}>
                  <span style={{ color: s.color, fontSize: "12px", lineHeight: 1 }}>{s.glyph}</span>
                  {t}
                </span>
              );
            })}
            <span className="flex items-center gap-1.5" style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>
              ⟶ edge points to the thing it produced/influenced; labels appear while highlighted
            </span>
          </div>
        </>
      )}
    </div>
  );
}
