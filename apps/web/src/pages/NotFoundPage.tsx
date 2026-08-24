import { useNavigate, useLocation, Link } from "react-router-dom";
import { C, FONT_MONO } from "../lib/ui";

const suggestions = [
  { to: "/", label: "Dashboard", desc: "Overview and recent analyses" },
  { to: "/dna", label: "DNA Analysis", desc: "8-dimension scoring" },
  { to: "/projects", label: "Projects", desc: "All repositories" },
  { to: "/graph", label: "Evolution Graph", desc: "Interactive history map" },
];

export default function NotFoundPage() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        backgroundColor: "#f8fafc",
        backgroundImage: "radial-gradient(circle at 50% 0%, rgba(99,102,241,0.07) 0%, transparent 60%)",
        textAlign: "center",
      }}
    >
      {/* Animated DNA graphic */}
      <div style={{ position: "relative", width: "120px", height: "120px", marginBottom: "32px" }}>
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
          <circle cx="60" cy="60" r="52" stroke="#e2e8f0" strokeWidth="1.5" strokeDasharray="6 4" />
          <circle cx="60" cy="18" r="8" fill="#ede9f2" stroke="#6366f1" strokeWidth="1.5" />
          <circle cx="98" cy="42" r="6" fill="#fce7f3" stroke="#ec4899" strokeWidth="1.5" />
          <circle cx="84" cy="90" r="7" fill="#d1fae5" stroke="#10b981" strokeWidth="1.5" />
          <circle cx="36" cy="90" r="7" fill="#fef9c3" stroke="#f59e0b" strokeWidth="1.5" />
          <circle cx="22" cy="42" r="6" fill="#ede9f2" stroke="#6366f1" strokeWidth="1.5" />
          <line x1="60" y1="26" x2="93" y2="46" stroke="#e2e8f0" strokeWidth="1" />
          <line x1="98" y1="48" x2="87" y2="83" stroke="#e2e8f0" strokeWidth="1" />
          <line x1="79" y1="92" x2="43" y2="92" stroke="#e2e8f0" strokeWidth="1" />
          <line x1="33" y1="83" x2="26" y2="48" stroke="#e2e8f0" strokeWidth="1" />
          <line x1="27" y1="38" x2="53" y2="21" stroke="#e2e8f0" strokeWidth="1" />
          <circle cx="60" cy="60" r="14" fill="#fee2e2" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="4 3" />
          <text x="60" y="65" textAnchor="middle" style={{ fontSize: "14px", fontWeight: 800, fill: "#ef4444", fontFamily: "JetBrains Mono" }}>
            ?
          </text>
        </svg>
      </div>

      {/* 404 label */}
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: "13px",
          fontWeight: 600,
          color: C.faint,
          letterSpacing: "0.1em",
          marginBottom: "12px",
        }}
      >
        ERROR 404
      </div>

      <h1
        style={{
          fontSize: "clamp(28px, 4vw, 40px)",
          fontWeight: 800,
          color: C.ink,
          letterSpacing: "-0.03em",
          lineHeight: 1.1,
          marginBottom: "12px",
        }}
      >
        This node doesn't exist
      </h1>

      <p style={{ fontSize: "15px", color: C.muted, maxWidth: "380px", lineHeight: 1.6, marginBottom: "8px" }}>
        The page at{" "}
        <code
          style={{
            fontFamily: FONT_MONO,
            fontSize: "13px",
            backgroundColor: "#f1f5f9",
            padding: "2px 6px",
            borderRadius: "4px",
            color: C.lavender,
          }}
        >
          {location.pathname}
        </code>{" "}
        wasn't found in the evolution graph.
      </p>

      <p style={{ fontSize: "13px", color: C.faint, marginBottom: "36px" }}>
        It may have been moved, deleted, or never existed.
      </p>

      {/* Actions */}
      <div className="flex items-center justify-center gap-3 flex-wrap mb-12">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all cursor-pointer"
          style={{ backgroundColor: "#ffffff", color: "#475569", border: `1px solid ${C.border}` }}
        >
          ← Go back
        </button>
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all cursor-pointer"
          style={{ backgroundColor: C.lavender, color: "#ffffff", border: "none", boxShadow: "0 4px 12px rgba(99,102,241,0.25)" }}
        >
          Dashboard →
        </button>
      </div>

      {/* Suggestions */}
      <div style={{ width: "100%", maxWidth: "480px" }}>
        <p
          style={{
            fontSize: "12px",
            fontWeight: 600,
            color: C.faint,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            marginBottom: "12px",
          }}
        >
          You might be looking for
        </p>
        <div className="grid grid-cols-2 gap-3">
          {suggestions.map((s) => (
            <Link key={s.to} to={s.to} style={{ textDecoration: "none" }}>
              <div
                className="p-4 rounded-xl text-left transition-all"
                style={{ backgroundColor: "#ffffff", border: `1px solid ${C.border}` }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "#c7d2fe";
                  (e.currentTarget as HTMLElement).style.backgroundColor = "#ede9f2";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "#e2e8f0";
                  (e.currentTarget as HTMLElement).style.backgroundColor = "#ffffff";
                }}
              >
                <div style={{ fontSize: "13px", fontWeight: 600, color: C.ink, marginBottom: "3px" }}>{s.label}</div>
                <div style={{ fontSize: "11px", color: C.faint }}>{s.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
