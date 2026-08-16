import type { ReactNode } from "react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="muted small">
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card mt">
      <div className="row">
        <span className="badge bad">Error</span>
        <span className="small">{message}</span>
        {onRetry && (
          <button className="secondary" onClick={onRetry} style={{ marginLeft: "auto" }}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="muted small">{children}</p>;
}