/**
 * Shared UI constants + primitives for the Figma "UI_UX Design Overview" design.
 * Colors/fonts mirror the Tailwind theme in index.css; use these for inline styles.
 */

export const C = {
  lavender: "#6366f1",
  lavenderSoft: "#ede9f2",
  lavenderMuted: "#c7d2fe",
  pinkSoft: "#fce7f3",
  pinkAccent: "#ec4899",
  ink: "#1e293b",
  body: "#334155",
  muted: "#64748b",
  faint: "#94a3b8",
  border: "#e2e8f0",
  borderLight: "#f1f5f9",
  pageBg: "#f8fafc",
  white: "#ffffff",
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  orange: "#f97316",
} as const;

export const FONT_MONO = "'JetBrains Mono', ui-monospace, monospace";
export const FONT_SANS = "'DM Sans', system-ui, sans-serif";

/** Score chip / bar coloring per the design spec. */
export function scoreColors(score: number | null): { bg: string; text: string; bar: string } {
  if (score === null) return { bg: C.borderLight, text: C.faint, bar: C.border };
  if (score >= 75) return { bg: "#d1fae5", text: "#065f46", bar: C.success };
  if (score >= 50) return { bg: "#fef9c3", text: "#713f12", bar: C.warning };
  if (score >= 25) return { bg: "#ffedd5", text: "#7c2d12", bar: C.orange };
  return { bg: "#fee2e2", text: "#7f1d1d", bar: C.error };
}

export function mono(size: number, weight: number | string = 500, color: string = C.ink) {
  return { fontFamily: FONT_MONO, fontSize: size, fontWeight: weight, color } as const;
}

export const panelStyle = {
  backgroundColor: C.white,
  border: `1px solid ${C.border}`,
} as const;

export const gradientBannerStyle = {
  background: "linear-gradient(135deg, #ede9f2 0%, #fce7f3 100%)",
  border: `1px solid ${C.lavenderMuted}`,
} as const;
