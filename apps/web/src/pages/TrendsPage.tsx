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
import { C, FONT_MONO, panelStyle } from "../lib/ui";
import { DIMENSION_LABELS } from "../lib/format";
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
  maintainability: "#6366f1",
  testing_maturity: "#10b981",
  documentation_quality: "#f59e0b",
  evolution_health: "#8b5cf6",
  delivery_readiness: "#ec4899",
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

  const projectAlerts = (alerts ?? []).filter((a) => (rules ?? []).some((r) => r.id === a.rule_id));

  const formError = createRule.isError ? (createRule.error as Error).message : null;

  const handleCreate = (e: FormEvent) => {
    e.preventDefault();
    createRule.mutate({ dimension, operator, threshold });
  };

  const selectStyle = {
    fontFamily: FONT_MONO,
    fontSize: "12px",
    border: `1px solid ${C.border}`,
    borderRadius: "6px",
    padding: "6px 10px",
    backgroundColor: "#ffffff" as string,
    color: C.ink,
  };

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <header className="mb-6">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 style={{ fontSize: "22px", fontWeight: 700, color: C.ink, letterSpacing: "-0.02em" }}>
              Trends &amp; Alerts
            </h1>
            <p style={{ fontSize: "13px", color: C.muted, marginTop: "4px" }}>
              DNA scores across snapshots; alert when a dimension crosses a threshold.
            </p>
          </div>
          <Link to={`/dna?project=${projectId}`} style={{ fontSize: "12px", color: C.lavender, textDecoration: "none", fontWeight: 500 }}>
            Back to DNA profile →
          </Link>
        </div>
      </header>

      {!hasTrends ? (
        <div className="rounded-xl p-5" style={panelStyle}>
          <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>Not enough data yet</h3>
          <p style={{ fontSize: "12px", color: C.muted }}>
            Run at least two analyses to see trends — re-analyze this project from its detail page or the
            DNA page.
          </p>
        </div>
      ) : (
        <section className="rounded-xl p-5 mb-6" style={panelStyle}>
          <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>Dimension trends</h3>
          <div className="mt-3" style={{ height: 360 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.borderLight} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: C.faint }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: C.faint, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}`, fontFamily: "DM Sans" }}
                  labelStyle={{ fontWeight: 600, color: C.ink }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: "DM Sans" }} />
                {DIMENSIONS.map((d) => (
                  <Line
                    key={d}
                    type="monotone"
                    dataKey={d}
                    name={DIMENSION_LABELS[d]}
                    stroke={DIMENSION_COLORS[d]}
                    strokeWidth={1.8}
                    dot={false}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p style={{ fontSize: "11px", color: C.faint }}>
            Gaps in a line mean the dimension's score was withheld (insufficient evidence).
          </p>
        </section>
      )}

      <section className="grid gap-4 md:grid-cols-2">
        {/* Alert rules */}
        <div className="rounded-xl p-5" style={panelStyle}>
          <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>Alert rules</h3>
          {rules?.length ? (
            <ul className="mt-3" style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {rules.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-2 flex-wrap">
                  <span style={{ fontSize: "13px", color: C.body }}>
                    <strong>{DIMENSION_LABELS[r.dimension] ?? r.dimension}</strong>{" "}
                    {r.operator === "lt" ? "below" : "above"}{" "}
                    <span style={{ fontFamily: FONT_MONO }}>{r.threshold}</span>
                  </span>
                  <button
                    onClick={() => deleteRule.mutate(r.id)}
                    disabled={deleteRule.isPending}
                    className="text-xs font-medium cursor-pointer"
                    style={{ background: "none", border: "none", color: C.error, padding: 0 }}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: "12px", color: C.faint }}>No rules yet.</p>
          )}

          <form className="mt-4" onSubmit={handleCreate}>
            <div className="flex items-center gap-2 flex-wrap">
              <select value={dimension} onChange={(e) => setDimension(e.target.value)} aria-label="Dimension" style={{ ...selectStyle, maxWidth: 220 }}>
                {DIMENSIONS.map((d) => (
                  <option key={d} value={d}>
                    {DIMENSION_LABELS[d] ?? d}
                  </option>
                ))}
              </select>
              <select value={operator} onChange={(e) => setOperator(e.target.value as "lt" | "gt")} aria-label="Operator" style={selectStyle}>
                <option value="lt">below</option>
                <option value="gt">above</option>
              </select>
              <input
                type="number"
                min={0}
                max={100}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                aria-label="Threshold"
                style={{ ...selectStyle, width: 72 }}
              />
              <button
                type="submit"
                disabled={createRule.isPending}
                className="px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer"
                style={{ backgroundColor: C.lavender, color: "#ffffff", border: "none" }}
              >
                Add rule
              </button>
            </div>
            {formError && (
              <p style={{ fontSize: "12px", color: C.error }}>{formError}</p>
            )}
          </form>
        </div>

        {/* Alerts */}
        <div className="rounded-xl p-5" style={panelStyle}>
          <h3 style={{ fontSize: "14px", fontWeight: 600, color: C.ink }}>Alerts</h3>
          {projectAlerts.length ? (
            <ul className="mt-3" style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
              {projectAlerts.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-2 flex-wrap">
                  <div style={{ fontSize: "13px", color: C.body }}>
                    <span
                      style={{
                        fontFamily: FONT_MONO,
                        fontSize: "11px",
                        fontWeight: 600,
                        padding: "2px 7px",
                        borderRadius: "4px",
                        backgroundColor: C.lavenderSoft,
                        color: C.lavender,
                      }}
                    >
                      {DIMENSION_LABELS[a.dimension] ?? a.dimension}
                    </span>{" "}
                    <span style={{ fontFamily: FONT_MONO, fontWeight: 700 }}>{a.new_value}</span>
                    {a.old_value !== null && (
                      <span style={{ fontSize: "12px", color: C.faint }}> (was {a.old_value})</span>
                    )}
                  </div>
                  <button
                    onClick={() => acknowledge.mutate(a.id)}
                    className="text-xs font-medium cursor-pointer"
                    style={{ background: "none", border: "none", color: C.lavender, padding: 0 }}
                  >
                    Acknowledge
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: "12px", color: C.faint }}>No active alerts.</p>
          )}
        </div>
      </section>
    </div>
  );
};

export default TrendsPage;
