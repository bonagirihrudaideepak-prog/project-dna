import { useMemo, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  useAlertRules,
  useAlerts,
  useAcknowledgeAlert,
  useCreateAlertRule,
  useDeleteAlertRule,
} from "../hooks/useAlerts";
import { useTrends } from "../hooks/useTrends";
import { ErrorState, LoadingState } from "../components/StateViews";
import type { TrendPoint } from "../lib/types";

const DIMENSIONS = [
  "technical_complexity",
  "maintainability",
  "testing_maturity",
  "documentation_quality",
  "evolution_health",
  "delivery_readiness",
  "scalability_readiness",
  "technical_debt_risk",
];

const DIMENSION_COLORS: Record<string, string> = {
  technical_complexity: "#6b7280",
  maintainability: "#3b82f6",
  testing_maturity: "#10b981",
  documentation_quality: "#f59e0b",
  evolution_health: "#8b5cf6",
  delivery_readiness: "#ef4444",
  scalability_readiness: "#14b8a6",
  technical_debt_risk: "#f97316",
};

export const TrendsPage = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const { data: trends, isLoading, isError, refetch } = useTrends(projectId);
  const { data: rules } = useAlertRules(projectId);
  const { data: alerts } = useAlerts();
  const acknowledge = useAcknowledgeAlert();
  const deleteRule = useDeleteAlertRule(projectId ?? "");
  const createRule = useCreateAlertRule(projectId);

  const [dimension, setDimension] = useState(DIMENSIONS[0]);
  const [operator, setOperator] = useState<"lt" | "gt">("lt");
  const [threshold, setThreshold] = useState(50);

  const chartData = useMemo(() => {
    const pts = trends ?? [];
    return pts.map((p: TrendPoint) => {
      const row: Record<string, string | number | null> = {
        label: (p.captured_at ?? p.created_at ?? "").slice(0, 10) || p.snapshot_id.slice(0, 8),
      };
      for (const d of DIMENSIONS) row[d] = p.scores?.[d] ?? null;
      return row;
    });
  }, [trends]);

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="Failed to load trends." onRetry={() => refetch()} />;

  const hasTrends = (trends?.length ?? 0) >= 2;

  const projectAlerts = (alerts ?? []).filter((a) =>
    (rules ?? []).some((r) => r.id === a.rule_id),
  );

  const formError = createRule.isError ? (createRule.error as Error).message : null;

  const handleCreate = (e: FormEvent) => {
    e.preventDefault();
    createRule.mutate({ dimension, operator, threshold });
  };

  return (
    <div className="min-h-screen bg-pageBg p-4 md:p-8">
      <header className="mb-6">
        <div className="row between wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-700">Trends &amp; Alerts</h1>
            <p className="text-slate-500 text-sm">
              DNA scores across snapshots; alert when a dimension crosses a threshold.
            </p>
          </div>
          <Link to={`/projects/${projectId}/dna`} className="text-slate-500 text-sm">
            Back to DNA profile
          </Link>
        </div>
      </header>

      {!hasTrends ? (
        <div className="card mt">
          <h3>Not enough data yet</h3>
          <p className="muted small">
            Run at least two analyses to see trends. Re-analyze this project from its detail page.
          </p>
        </div>
      ) : (
        <section className="card mt">
          <h3>Dimension trends</h3>
          <div className="mt" style={{ height: 360 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                {DIMENSIONS.map((d) => (
                  <Line
                    key={d}
                    type="monotone"
                    dataKey={d}
                    stroke={DIMENSION_COLORS[d]}
                    dot={false}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="muted small">
            Gaps in a line mean the dimension's score was withheld (insufficient evidence).
          </p>
        </section>
      )}

      <section className="grid grid-2 mt-lg">
        <div className="card">
          <h3>Alert rules</h3>
          {rules?.length ? (
            <ul className="mt" style={{ listStyle: "none", padding: 0 }}>
              {rules.map((r) => (
                <li key={r.id} className="row between mb">
                  <span>
                    <strong>{r.dimension}</strong> {r.operator === "lt" ? "below" : "above"} {r.threshold}
                  </span>
                  <button
                    className="small"
                    onClick={() => deleteRule.mutate(r.id)}
                    disabled={deleteRule.isPending}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">No rules yet.</p>
          )}

          <form
            className="mt"
            onSubmit={handleCreate}
          >
            <div className="row wrap">
              <select value={dimension} onChange={(e) => setDimension(e.target.value)}>
                {DIMENSIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
              <select value={operator} onChange={(e) => setOperator(e.target.value as "lt" | "gt")}>
                <option value="lt">below</option>
                <option value="gt">above</option>
              </select>
              <input
                type="number"
                min={0}
                max={100}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                style={{ width: 80 }}
              />
              <button type="submit" disabled={createRule.isPending}>
                Add rule
              </button>
            </div>
            {formError && <p className="small bad mt">{formError}</p>}
          </form>
        </div>

        <div className="card">
          <h3>Alerts</h3>
          {projectAlerts.length ? (
            <ul className="mt" style={{ listStyle: "none", padding: 0 }}>
              {projectAlerts.map((a) => (
                <li key={a.id} className="row between mb">
                  <div>
                    <span className="badge accent">{a.dimension}</span>{" "}
                    {a.new_value !== null && <span>{a.new_value}</span>}
                    <span className="muted small">
                      {" "}
                      {a.old_value !== null && `(was ${a.old_value})`}
                    </span>
                  </div>
                  <button className="small" onClick={() => acknowledge.mutate(a.id)}>
                    Acknowledge
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">No active alerts.</p>
          )}
        </div>
      </section>
    </div>
  );
};

export default TrendsPage;