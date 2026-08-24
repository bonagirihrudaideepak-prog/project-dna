import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { useSnapshotId } from "../hooks/useJob";
import { useTimeline } from "../hooks/useTimeline";
import { C, FONT_MONO, panelStyle } from "../lib/ui";

const TYPE_CFG: Record<string, { color: string; bg: string; label: string }> = {
  release: { color: C.lavender, bg: C.lavenderSoft, label: "Release" },
  decision: { color: "#10b981", bg: "#d1fae5", label: "Decision" },
  experiment: { color: "#f59e0b", bg: "#fef9c3", label: "Experiment" },
  pr: { color: "#ec4899", bg: "#fce7f3", label: "Pull Request" },
  cluster: { color: "#0ea5e9", bg: "#e0f2fe", label: "Cluster" },
  dependency: { color: "#64748b", bg: "#f1f5f9", label: "Dependency" },
};

function cfgFor(type: string) {
  return (
    TYPE_CFG[type] ?? {
      color: C.lavender,
      bg: C.lavenderSoft,
      label: type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, " "),
    }
  );
}

export default function TimelinePage() {
  const { user, projects, loading: spineLoading } = useUserAndProjects();
  const { project, projectId } = useActiveProject(projects);
  const { snapshotId, loading: snapLoading } = useSnapshotId(projectId);
  const { data, isLoading, isError, error, refetch } = useTimeline(snapshotId);
  const [filter, setFilter] = useState<string>("all");

  const events = useMemo(() => data ?? [], [data]);

  const presentTypes = useMemo(() => {
    const set = new Set<string>();
    for (const e of events) if (e.type) set.add(e.type);
    return Array.from(set);
  }, [events]);

  const filtered =
    filter === "all" ? events : events.filter((e) => e.type === filter);

  if (spineLoading || snapLoading || isLoading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader
        title="Timeline"
        subtitle={`Reconstructed history of releases, decisions, and experiments${project ? ` — ${project.full_name}` : ""}`}
      />

      {!user ? (
        <EmptyState>
          <Link to="/login" style={{ color: C.lavender, fontWeight: 600 }}>
            Sign in with GitHub
          </Link>{" "}
          to view reconstructed project timelines.
        </EmptyState>
      ) : projects.length === 0 ? (
        <EmptyState>No repositories yet — run an analysis first.</EmptyState>
      ) : !snapshotId ? (
        <EmptyState>
          No completed analysis for this repository yet. Run one from{" "}
          <Link to={`/dna?project=${projectId}`} style={{ color: C.lavender, fontWeight: 600 }}>
            DNA Analysis
          </Link>
          .
        </EmptyState>
      ) : isError ? (
        <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
      ) : (
        <>
          {/* Filters */}
          <div className="flex items-center gap-2 mb-8 flex-wrap">
            <button
              onClick={() => setFilter("all")}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer"
              style={{
                backgroundColor: filter === "all" ? C.lavenderSoft : C.pageBg,
                color: filter === "all" ? C.lavender : C.muted,
                border: `1px solid ${filter === "all" ? C.lavenderMuted : C.border}`,
              }}
            >
              All events ({events.length})
            </button>
            {presentTypes.map((t) => {
              const cfg = cfgFor(t);
              const active = filter === t;
              return (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer"
                  style={{
                    backgroundColor: active ? cfg.bg : C.pageBg,
                    color: active ? cfg.color : C.muted,
                    border: `1px solid ${active ? cfg.color + "55" : C.border}`,
                  }}
                >
                  {cfg.label} ({events.filter((e) => e.type === t).length})
                </button>
              );
            })}
          </div>

          {filtered.length === 0 ? (
            <EmptyState>No timeline events found for this snapshot.</EmptyState>
          ) : (
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute hidden md:block" style={{ left: "140px", top: 0, bottom: 0, width: "1px", backgroundColor: C.border }} />

              <div className="space-y-6">
                {[...filtered]
                  .reverse()
                  .map((event) => {
                    const cfg = cfgFor(event.type);
                    return (
                      <div key={event.id} className="flex items-start gap-6">
                        {/* Date */}
                        <div className="hidden md:block" style={{ width: "130px", flexShrink: 0, textAlign: "right", paddingTop: "10px" }}>
                          <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>
                            {event.occurred_at
                              ? new Date(event.occurred_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                              : "date unknown"}
                          </span>
                        </div>

                        {/* Dot */}
                        <div className="hidden md:flex" style={{ flexShrink: 0, width: "22px", justifyContent: "center", paddingTop: "12px" }}>
                          <div
                            style={{
                              width: "10px",
                              height: "10px",
                              borderRadius: "50%",
                              backgroundColor: cfg.color,
                              border: `2px solid ${cfg.color}33`,
                              boxShadow: `0 0 0 3px ${cfg.bg}`,
                            }}
                          />
                        </div>

                        {/* Card */}
                        <div className="flex-1 rounded-xl p-4 transition-all min-w-0" style={panelStyle}>
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: 600,
                                padding: "2px 7px",
                                borderRadius: "4px",
                                backgroundColor: cfg.bg,
                                color: cfg.color,
                                textTransform: "uppercase",
                                letterSpacing: "0.04em",
                              }}
                            >
                              {cfg.label}
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 600, color: C.ink }}>{event.title || "Unknown event"}</span>
                            <span className="md:hidden" style={{ marginLeft: "auto", fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>
                              {event.occurred_at ? new Date(event.occurred_at).toLocaleDateString() : ""}
                            </span>
                          </div>
                          {event.summary && (
                            <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.6 }}>{event.summary}</p>
                          )}
                          <div className="flex items-center gap-2 mt-2">
                            <span style={{ fontFamily: FONT_MONO, fontSize: "10px", color: C.faint }}>
                              provenance: {event.provenance}
                            </span>
                            {(event.components ?? []).slice(0, 4).map((comp) => (
                              <span key={comp} style={{ fontFamily: FONT_MONO, fontSize: "10px", color: C.muted, backgroundColor: C.pageBg, padding: "1px 6px", borderRadius: "3px" }}>
                                {comp}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
