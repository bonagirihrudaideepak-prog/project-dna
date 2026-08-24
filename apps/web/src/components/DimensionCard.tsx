import { useState } from "react";
import { C, FONT_MONO, scoreColors } from "../lib/ui";

export interface DimensionCardProps {
  name: string;
  /** null = withheld (insufficient coverage) — never rendered as zero */
  score: number | null;
  confidence: string;
  direction: string;
  description?: string;
  limitations: string[];
  trend?: "up" | "down" | "stable";
}

function TrendIcon({ trend }: { trend?: "up" | "down" | "stable" }) {
  if (trend === "up") return <span style={{ color: C.success, fontSize: "12px" }}>↑</span>;
  if (trend === "down") return <span style={{ color: C.error, fontSize: "12px" }}>↓</span>;
  if (trend === "stable") return <span style={{ color: C.faint, fontSize: "12px" }}>→</span>;
  return null;
}

export default function DimensionCard({ dim }: { dim: DimensionCardProps }) {
  const [expanded, setExpanded] = useState(false);
  const effective = dim.direction === "lower_is_better" && dim.score !== null ? 100 - dim.score : dim.score;
  const colors = scoreColors(dim.score === null ? null : effective);
  const barWidth = dim.score === null ? 0 : effective;

  return (
    <div
      className="rounded-xl p-4 cursor-pointer transition-all"
      style={{
        backgroundColor: C.white,
        border: `1px solid ${C.border}`,
        boxShadow: expanded ? "0 4px 16px rgba(99,102,241,0.08)" : "0 1px 3px rgba(0,0,0,0.04)",
      }}
      onClick={() => setExpanded(!expanded)}
      aria-expanded={expanded}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span style={{ fontWeight: 600, fontSize: "13px", color: C.ink }}>{dim.name}</span>
            <TrendIcon trend={dim.trend} />
          </div>
          <div className="flex items-center gap-2 mb-3">
            <span
              style={{
                fontFamily: FONT_MONO,
                fontSize: "11px",
                padding: "2px 6px",
                borderRadius: "4px",
                backgroundColor: colors.bg,
                color: colors.text,
                fontWeight: 500,
              }}
            >
              {dim.confidence}
            </span>
            {dim.direction === "lower_is_better" && (
              <span style={{ fontSize: "10px", color: C.faint }}>lower is better</span>
            )}
          </div>

          {/* Progress bar — withheld scores render as an empty track with — */}
          <div className="flex items-center gap-3">
            <div className="flex-1 rounded-full overflow-hidden" style={{ height: "6px", backgroundColor: C.borderLight }}>
              {dim.score !== null && (
                <div className="h-full rounded-full transition-all" style={{ width: `${barWidth}%`, backgroundColor: colors.bar }} />
              )}
            </div>
            <span
              style={{
                fontFamily: FONT_MONO,
                fontSize: "13px",
                fontWeight: 600,
                color: dim.score === null ? C.faint : C.ink,
                minWidth: "32px",
                textAlign: "right",
              }}
            >
              {dim.score ?? "—"}
            </span>
          </div>
        </div>

        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          style={{ flexShrink: 0, color: C.faint, transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
        >
          <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      {expanded && (
        <div className="mt-3 pt-3" style={{ borderTop: `1px solid ${C.borderLight}` }}>
          {(dim.description || dim.limitations.length > 0) && (
            <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.6, marginBottom: dim.limitations.length ? "10px" : 0 }}>
              {dim.description}
            </p>
          )}
          {dim.limitations.length > 0 && (
            <>
              <div style={{ fontSize: "10px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>
                Limitations
              </div>
              <ul className="space-y-1">
                {dim.limitations.map((lim, i) => (
                  <li key={i} className="flex items-start gap-2" style={{ fontSize: "11px", color: C.faint }}>
                    <span style={{ color: C.warning, marginTop: "1px", flexShrink: 0 }}>•</span>
                    {lim}
                  </li>
                ))}
              </ul>
            </>
          )}
          {dim.score === null && (
            <p style={{ fontSize: "11px", color: C.faint, marginTop: "6px" }}>
              Score withheld — insufficient evidence coverage.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
