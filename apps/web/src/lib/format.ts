export function confidenceColor(confidence: string): string {
  switch (confidence) {
    case "high":
      return "var(--green)";
    case "moderate":
      return "var(--yellow)";
    case "low":
      return "var(--red)";
    default:
      return "var(--text-muted)";
  }
}

export function confidenceToneClass(confidence: string): string {
  switch (confidence) {
    case "high":
      return "ok";
    case "moderate":
      return "warn";
    case "low":
      return "bad";
    default:
      return "";
  }
}

export function directionLabel(direction: string): string {
  switch (direction) {
    case "higher_is_better":
      return "Higher is better";
    case "lower_is_better":
      return "Lower is better";
    default:
      return "Descriptive";
  }
}

export function provenanceColor(provenance: string): string {
  switch (provenance) {
    case "observed":
      return "var(--green)";
    case "rule-derived":
      return "var(--teal)";
    case "suggested":
      return "var(--yellow)";
    case "user":
    case "user-confirmed":
      return "var(--purple)";
    default:
      return "var(--text-muted)";
  }
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function scoreTone(score: number | null): "good" | "warn" | "bad" | "unknown" {
  if (score === null) return "unknown";
  if (score >= 70) return "good";
  if (score >= 45) return "warn";
  return "bad";
}

export function scoreLabel(score: number | null): string {
  return score === null ? "—" : String(score);
}

export const DIMENSION_LABELS: Record<string, string> = {
  technical_complexity: "Technical Complexity",
  maintainability: "Maintainability",
  testing_maturity: "Testing Maturity",
  documentation_quality: "Documentation Quality",
  evolution_health: "Evolution Health",
  delivery_readiness: "Delivery Readiness",
  scalability_readiness: "Scalability Readiness",
  technical_debt_risk: "Technical Debt Risk",
};