import type { ReactNode } from "react";
import { C } from "../lib/ui";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-8 justify-center" style={{ color: C.muted, fontSize: "13px" }}>
      <span className="loading-spinner" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-xl p-4 flex items-center gap-3 flex-wrap"
      style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", marginTop: 16 }}
    >
      <span
        style={{
          fontSize: "11px",
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: "4px",
          backgroundColor: "#b91c1c",
          color: C.white,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        Error
      </span>
      <span style={{ fontSize: "13px", color: "#7f1d1d", flex: 1, minWidth: 200 }}>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
          style={{ backgroundColor: C.white, border: `1px solid #fca5a5`, color: "#7f1d1d" }}
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div
      className="rounded-xl p-6 text-center"
      style={{ backgroundColor: C.pageBg, border: `1px dashed ${C.border}`, color: C.muted, fontSize: "13px" }}
    >
      {children}
    </div>
  );
}
