import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useJob, useSnapshotId } from "../hooks/useJob";

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data: project } = useQuery({ queryKey: ["project", id], queryFn: () => api.project(id!) });
  const { snapshotId, loading } = useSnapshotId(id);
  const [jobId, setJobId] = useState<string | null>(null);
  const { job, error } = useJob(jobId, () => {
    setJobId(null);
    qc.invalidateQueries({ queryKey: ["project", id] });
    qc.invalidateQueries({ queryKey: ["snapshots", id] });
  });

  return (
    <div>
      {project && (
        <div className="row between wrap">
          <div>
            <h1 className="mb">{project.full_name}</h1>
            <p className="muted small mb">
              {project.description}
              <span className="badge accent" style={{ marginLeft: 8 }}>
                {project.default_branch}
              </span>
            </p>
          </div>
          <div className="row">
            <button
              onClick={async () => {
                const j = await api.queueAnalysis(project.id);
                setJobId(j.id);
              }}
            >
              Re-analyze
            </button>
          </div>
        </div>
      )}

      {job && (
        <div className="card mt">
          <div className="row between">
            <strong>Analysis running…</strong>
            <span className="badge accent">{job.state}</span>
          </div>
          <div className="progress-track mt">
            <div className="progress-fill" style={{ width: `${job.progress}%` }} />
          </div>
          <p className="small muted">{job.phase}</p>
        </div>
      )}
      {error && (
        <div className="card mt">
          <span className="badge bad">Failed</span> {error}
        </div>
      )}

      <div className="mt-lg">
        <div className="grid grid-2">
          <Link to={`/projects/${id}/trends`} className="card" style={{ color: "var(--text)" }}>
            <h3>Trends &amp; Alerts</h3>
            <p className="muted small">DNA scores across snapshots and threshold alerts.</p>
          </Link>
          <Link to={`/projects/${id}/dna`} className="card" style={{ color: "var(--text)" }}>
            <h3>DNA Profile</h3>
            <p className="muted small">Eight explainable dimensions with evidence drill-down.</p>
          </Link>
          <Link to={`/projects/${id}/timeline`} className="card" style={{ color: "var(--text)" }}>
            <h3>Timeline</h3>
            <p className="muted small">Releases, PRs, clusters, dependency changes, and decisions.</p>
          </Link>
          <Link to={`/projects/${id}/decisions`} className="card" style={{ color: "var(--text)" }}>
            <h3>Decisions</h3>
            <p className="muted small">Decision Archaeology records with alternatives and outcomes.</p>
          </Link>
          <Link to={`/projects/${id}/experiments`} className="card" style={{ color: "var(--text)" }}>
            <h3>Experiments</h3>
            <p className="muted small">Preserved failed experiments and their lessons.</p>
          </Link>
          <Link to={`/projects/${id}/graph`} className="card" style={{ color: "var(--text)" }}>
            <h3>Evolution Graph</h3>
            <p className="muted small">Events, decisions, components, and outcomes as a graph.</p>
          </Link>
          <Link to={`/projects/${id}/exports`} className="card" style={{ color: "var(--text)" }}>
            <h3>Exports</h3>
            <p className="muted small">JSON and print-friendly project report.</p>
          </Link>
        </div>
      </div>
    </div>
  );
}