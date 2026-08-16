import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import { useSnapshotId } from "../hooks/useJob";
import { confidenceColor, confidenceToneClass, DIMENSION_LABELS, directionLabel } from "../lib/format";
import { ErrorState, LoadingState } from "../components/StateViews";
import type { DNAScore } from "../lib/types";

export function DNAPage() {
  const { id } = useParams<{ id: string }>();
  const { snapshotId } = useSnapshotId(id);
  const {
    data: dna,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["dna", snapshotId],
    queryFn: () => api.dna(snapshotId!),
    enabled: !!snapshotId,
  });
  const [selected, setSelected] = useState<DNAScore | null>(null);

  if (isLoading && !dna) return <LoadingState />;
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />;
  if (!dna || dna.length === 0)
    return <p className="muted">No DNA data yet. Run an analysis first.</p>;

  const radarData = dna.map((d) => ({
    dimension: DIMENSION_LABELS[d.dimension] || d.dimension,
    value: d.score ?? 0,
    full: DIMENSION_LABELS[d.dimension] || d.dimension,
  }));
  const barData = dna.map((d) => ({
    name: DIMENSION_LABELS[d.dimension] || d.dimension,
    score: d.score ?? 0,
    coverage: Math.round(d.coverage * 100),
    direction: d.direction,
    dim: d.dimension,
  }));

  const visible = selected ?? dna[0];

  return (
    <div>
      <h1 className="mb">DNA Profile</h1>
      <div className="two-col">
        <div>
          <div className="card">
            <h3>Radar</h3>
            <div className="radar-wrap">
              <ResponsiveContainer width="100%" height={360}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="full" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.35} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card mt">
            <h3>Dimensions</h3>
            <ResponsiveContainer width="100%" height={barData.length * 34 + 40}>
              <BarChart layout="vertical" data={barData} margin={{ left: 20 }}>
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={190}
                  tick={{ fill: "var(--text)", fontSize: 12 }}
                />
                <Tooltip />
                <Bar dataKey="score" fill="var(--accent)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
            {barData.map((b) => (
              <button
                key={b.dim}
                className="secondary"
                style={{ margin: 4, padding: "6px 10px", fontSize: 12 }}
                onClick={() => setSelected(dna.find((d) => d.dimension === b.dim)!)}
              >
                {b.name}
              </button>
            ))}
          </div>
        </div>

        <div>
          {visible && (
            <div className="card">
              <h3 className="mb">{DIMENSION_LABELS[visible.dimension] || visible.dimension}</h3>
              <div className="row">
                <span className="score-big" style={{ color: confidenceColor(visible.confidence) }}>
                  {visible.score ?? "—"}
                </span>
                <div>
                  <div className="direction-label">{directionLabel(visible.direction)}</div>
                  <div className="badge" style={{ background: "var(--bg-hover)" }}>
                    coverage {Math.round(visible.coverage * 100)}%
                  </div>
                  <span className={`badge ${confidenceToneClass(visible.confidence)}`}>
                    {visible.confidence}
                  </span>
                </div>
              </div>
              <p className="small muted">
                Model {visible.model_version}. {visible.score === null ? "Insufficient evidence — score withheld." : ""}
              </p>

              <h4 className="mb">Indicators</h4>
              {(visible.explanation?.indicators ?? visible.evidence ?? []).map((ind) => (
                <div key={ind.key} className="card" style={{ padding: 12, marginBottom: 8 }}>
                  <div className="row between">
                    <strong className="small">{ind.key}</strong>
                    <span className="small muted">
                      weight contribution {Math.round(ind.normalized_value * 100)}% · quality{" "}
                      {Math.round(ind.quality * 100)}%
                    </span>
                  </div>
                  <div className="progress-track mt" style={{ height: 6 }}>
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.round(ind.normalized_value * 100)}%`, background: "var(--teal)" }}
                    />
                  </div>
                  <div className="small muted mt" style={{ fontSize: 11 }}>
                    evidence: {(ind.evidence_ids ?? []).slice(0, 5).join(", ") || "—"}
                  </div>
                </div>
              ))}

              {visible.explanation?.limitations?.length ? (
                <>
                  <h4 className="mb">Limitations</h4>
                  <ul className="small muted">
                    {visible.explanation.limitations.map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}