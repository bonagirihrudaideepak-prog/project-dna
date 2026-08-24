import { Component, type ErrorInfo, type ReactNode } from "react";
import { C } from "../lib/ui";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Uncaught render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="rounded-xl p-5 max-w-screen-xl mx-auto my-8"
          style={{ backgroundColor: C.white, border: "1px solid #fca5a5" }}
        >
          <div className="flex items-center gap-3 mb-3 flex-wrap">
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: "4px",
                backgroundColor: "#b91c1c",
                color: C.white,
                textTransform: "uppercase",
              }}
            >
              Unexpected error
            </span>
            <span style={{ fontSize: "13px", color: "#7f1d1d" }}>{this.state.error.message}</span>
          </div>
          <button
            className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
            style={{ backgroundColor: C.lavenderSoft, border: `1px solid ${C.lavenderMuted}`, color: C.lavender }}
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
