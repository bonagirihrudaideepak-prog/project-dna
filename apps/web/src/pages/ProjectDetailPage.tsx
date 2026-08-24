import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { useJob, useSnapshotId } from "../hooks/useJob";
import { LoadingState } from "../components/StateViews";
import { C, FONT_MONO, panelStyle } from "../lib/ui";

const LINKS = [
  { to: "trends", title: "Trends & Alerts", desc: "DNA scores across snapshots and threshold alerts." },
  { to: "/dna", title: "DNA Profile", desc: "Eight explainable dimensions with evidence drill-down." },
  { to: "/timeline", title: "Timeline", desc: "Releases, PRs, clusters, dependency changes, and decisions." },
  { to: "/decisions", title: "Decisions", desc: "Decision Archaeology records with alternatives and outcomes." },
  { to: "/experiments", title: "Experiments", desc: "Preserved failed experiments and their lessons." },
  { to: "/graph", title: "Evolution Graph", desc: "Events, decisions, components, and outcomes as a graph." },
  { to: "/exports", title: "Exports", desc: "Structured JSON and printable HTML project report." },
];

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data: project } = useQuery({ queryKey: queryKeys.project(id), queryFn: () => api.project(id!) });
  const { snapshotId, loading } = useSnapshotId(id);
  const [jobId, setJobId] = useState<string | null>(null);
  const [queueing, setQueueing] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const { job, error } = useJob(jobId, () => {
    setJobId(null);
    qc.invalidateQueries({ queryKey: queryKeys.project(id) });
    qc.invalidateQueries({ queryKey: queryKeys.snapshots(id) });
  });

  const queueAnalysis = async (projectId: string) => {
    setQueueError(null);
    setQueueing(true);
    try {
      const j = await api.queueAnalysis(projectId);
      setJobId(j.id);
    } catch (e) {
      setQueueError((e as Error).message);
    } finally {
      setQueueing(false);
    }
  };

  if (!project && !queueError) return <LoadingState />;

  const hrefFor = (to: string) => (to.startsWith("/") ? `${to}?project=${id}` : `/projects/${id}/${to}`);

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      {/* Header */}
      {project && (
        <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
          <div className="min-w-0">
            <Link to="/projects" style={{ fontSize: "12px", color: C.faint, textDecoration: "none" }}>
              ← All projects
            </Link>
            <h1 style={{ fontFamily: FONT_MONO, fontSize: "20px", fontWeight: 700, color: C.ink, letterSpacing: "-0.02em", marginTop: "4px" }}>
              {project.full_name}
            </h1>
            <p className="flex items-center gap-2 flex-wrap" style={{ fontSize: "13px", color: C.muted, marginTop: "4px" }}>
              {project.description}
              <span
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: "10px",
                  fontWeight: 600,
                  padding: "2px 7px",
                  borderRadius: "4px",
                  backgroundColor: C.lavenderSoft,
                  color: C.lavender,
                }}
              >
                {project.default_branch}
              </span>
            </p>
          </div>
          <button
            onClick={() => void queueAnalysis(project.id)}
            disabled={queueing || !!jobId}
            className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
            style={{
              backgroundColor: queueing || jobId ? C.lavenderMuted : C.lavender,
              color: "#ffffff",
              border: "none",
            }}
          >
            Re-analyze
          </button>
        </div>
      )}

      {queueError && (
        <div className="rounded-xl p-4 mb-4" style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", fontSize: "13px", color: "#7f1d1d" }}>
          Failed to queue analysis: {queueError}
        </div>
      )}

      {/* Job progress */}
      {job && (
        <div className="rounded-xl p-5 mb-6" style={panelStyle}>
          <div className="flex items-center justify-between mb-2">
            <span style={{ fontSize: "13px", fontWeight: 600, color: C.ink }}>Analysis running…</span>
            <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.lavender }}>{job.state}</span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: "6px", backgroundColor: C.borderLight }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${job.progress}%`, backgroundColor: C.lavender }} />
          </div>
          <p style={{ fontSize: "12px", color: C.muted, marginTop: "6px" }}>{job.phase}</p>
        </div>
      )}
      {error && (
        <div className="rounded-xl p-4 mb-6" style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", fontSize: "13px", color: "#7f1d1d" }}>
          <strong>Failed:</strong> {error}
        </div>
      )}

      {!loading && snapshotId ? (
        <p style={{ fontSize: "12px", fontFamily: FONT_MONO, color: C.success, marginBottom: "24px" }}>
          ● Snapshot {snapshotId.slice(0, 8)} ready
        </p>
      ) : null}

      {/* Feature grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {LINKS.map((l) => (
          <Link key={l.title} to={hrefFor(l.to)} style={{ textDecoration: "none" }}>
            <div className="rounded-xl p-5 h-full transition-all cursor-pointer" style={panelStyle}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink, marginBottom: "6px" }}>{l.title}</h3>
              <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.6, marginBottom: 0 }}>{l.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default ProjectDetailPage;
