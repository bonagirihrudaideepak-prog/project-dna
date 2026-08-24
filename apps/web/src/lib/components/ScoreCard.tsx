import { forwardRef, type HTMLAttributes } from "react";
import { cn2 } from "../utils";

export interface ScoreCardProps extends HTMLAttributes<HTMLDivElement> {
  dimension: string;
  score?: number;
  coverage: number;
  confidence: "insufficient" | "low" | "moderate" | "high";
  direction: "lower_is_better" | "higher_is_better";
  limitations?: string[];
  onAnalyze?: () => void;
}

export const ScoreCard = forwardRef<HTMLDivElement, ScoreCardProps>((props, ref) => {
  const {
    dimension,
    score,
    coverage,
    confidence,
    direction,
    limitations = [],
    onAnalyze,
    ...otherProps
  } = props;

  const directionLabel =
    direction === "lower_is_better"
      ? "lower is better"
      : "higher is better";

  return (
    <div
      ref={ref}
      className={cn2(
        "card p-0", // p-6 set via parent; card has internal spacing via its own structure
        "group"
      )}
      {...otherProps}
    >
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-slate-500">{dimension}</span>
        <span className="text-2xl font-bold text-slate-700">
          {score !== undefined ? `${score}/100` : "—"}
        </span>
      </div>
      <div className="w-full h-6 rounded-full bg-slate-100 overflow-hidden mt-3">
        <div
          className="h-full rounded-full bg-lavender-primary"
          style={{ width: `${coverage * 100}%` }}
        ></div>
      </div>
      <p className="text-sm text-slate-500 mt-1">
        Coverage: {Math.round(coverage * 100)}%
      </p>
      <p className="text-xs text-slate-500 mt-1">
        Confidence: {capitalizeConfidence(confidence)}
      </p>
      {limitations.length > 0 && (
        <div className="mt-1 text-slate-400 text-xs">
          <strong>Limitations:</strong>
          {limitations.map((lim, i) => (
            <span key={i} className="block pl-1">
              {lim}
            </span>
          ))}
        </div>
      )}
    </div>
  );
});

function capitalizeConfidence(c: string) {
  return c.charAt(0).toUpperCase() + c.slice(1);
}

ScoreCard.displayName = "ScoreCard";

export default ScoreCard;