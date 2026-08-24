import { useNavigate } from "react-router-dom";
import { Logo } from "../components/NavMenu";
import { C, FONT_MONO, panelStyle } from "../lib/ui";

const features = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="8" stroke="#6366f1" strokeWidth="1.5" />
        <path d="M7 10l2 2 4-4" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "8-Dimension DNA Profile",
    desc: "Maintainability, testing maturity, documentation, evolution health, delivery readiness, scalability, complexity, and debt risk — all scored and explained.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M4 10h12M10 4l6 6-6 6" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "Reconstructed Timeline",
    desc: "Decisions, experiments, and architectural pivots surfaced automatically from commit history, PR descriptions, and branch patterns.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <rect x="3" y="3" width="6" height="6" rx="1.5" stroke="#f59e0b" strokeWidth="1.5" />
        <rect x="11" y="3" width="6" height="6" rx="1.5" stroke="#f59e0b" strokeWidth="1.5" />
        <rect x="3" y="11" width="6" height="6" rx="1.5" stroke="#f59e0b" strokeWidth="1.5" />
        <rect x="11" y="11" width="6" height="6" rx="1.5" stroke="#f59e0b" strokeWidth="1.5" />
      </svg>
    ),
    title: "Side-by-Side Comparison",
    desc: "Compare repositories across all 8 dimensions to identify leaders, laggards, and cross-team learning opportunities.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 3v10M7 11l3 3 3-3M4 16h12" stroke="#ec4899" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "Export Everywhere",
    desc: "Download results as structured JSON for integrations or a print-friendly HTML report for wikis and documentation.",
  },
];

const stats = [
  { value: "8", label: "DNA dimensions" },
  { value: "0–100", label: "explainable scores" },
  { value: "100%", label: "evidence-backed" },
  { value: "JSON/HTML", label: "report exports" },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const startGithub = () => (window.location.href = "/api/v1/auth/github/start");

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f8fafc" }}>
      {/* Minimal landing nav */}
      <header style={{ borderBottom: `1px solid ${C.border}`, backgroundColor: "#ffffff" }}>
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Logo />
            <span style={{ fontWeight: 700, fontSize: "15px", color: C.ink, letterSpacing: "-0.02em" }}>
              Project DNA
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/login")}
              style={{ fontSize: "13px", color: C.muted, fontWeight: 500, background: "none", border: "none", cursor: "pointer" }}
            >
              Sign in
            </button>
            <button
              onClick={() => navigate("/auth")}
              className="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
              style={{ backgroundColor: C.lavender, color: "#ffffff", border: "none" }}
            >
              Get started →
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section style={{ padding: "80px 24px 72px", textAlign: "center" }}>
        <div className="max-w-2xl mx-auto">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-6"
            style={{ backgroundColor: C.lavenderSoft, border: `1px solid ${C.lavenderMuted}` }}
          >
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "#10b981", display: "inline-block" }} />
            <span style={{ fontSize: "12px", fontWeight: 500, color: "#4338ca" }}>
              Explainable software archaeology
            </span>
          </div>

          <h1
            style={{
              fontSize: "clamp(32px, 5vw, 52px)",
              fontWeight: 800,
              color: C.ink,
              letterSpacing: "-0.03em",
              lineHeight: 1.1,
              marginBottom: "20px",
            }}
          >
            Software archaeology
            <br />
            <span style={{ color: C.lavender }}>for your codebase</span>
          </h1>

          <p style={{ fontSize: "16px", color: C.muted, lineHeight: 1.7, maxWidth: "480px", margin: "0 auto 36px" }}>
            Project DNA analyzes a repository's code, history, and tooling to produce an explainable,
            8-dimension profile of its health, complexity, and evolution.
          </p>

          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button
              onClick={startGithub}
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer"
              style={{ backgroundColor: C.lavender, color: "#ffffff", border: "none", boxShadow: "0 4px 14px rgba(99,102,241,0.35)" }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path fillRule="evenodd" clipRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" fill="currentColor" />
              </svg>
              Connect GitHub
            </button>
            <button
              onClick={() => navigate("/methodology")}
              className="px-6 py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer"
              style={{ backgroundColor: "#ffffff", color: "#475569", border: `1px solid ${C.border}` }}
            >
              How scoring works →
            </button>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <section style={{ borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`, backgroundColor: "#ffffff" }}>
        <div className="max-w-screen-xl mx-auto px-6 py-8 grid grid-cols-2 gap-6 md:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div style={{ fontFamily: FONT_MONO, fontSize: "28px", fontWeight: 800, color: C.lavender, lineHeight: 1 }}>
                {s.value}
              </div>
              <div style={{ fontSize: "13px", color: C.faint, marginTop: "4px" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-screen-xl mx-auto px-6 py-16">
        <h2
          style={{
            fontSize: "22px",
            fontWeight: 700,
            color: C.ink,
            letterSpacing: "-0.02em",
            marginBottom: "32px",
            textAlign: "center",
          }}
        >
          Everything your team needs to understand a codebase
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => (
            <div key={f.title} className="rounded-xl p-5" style={panelStyle}>
              <div className="mb-3">{f.icon}</div>
              <h3 style={{ fontSize: "13px", fontWeight: 700, color: C.ink, marginBottom: "6px" }}>{f.title}</h3>
              <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.65 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-screen-xl mx-auto px-6 pb-16">
        <div
          className="rounded-2xl p-10 text-center"
          style={{ background: "linear-gradient(135deg, #ede9f2 0%, #fce7f3 100%)", border: `1px solid ${C.lavenderMuted}` }}
        >
          <h2 style={{ fontSize: "24px", fontWeight: 800, color: C.ink, letterSpacing: "-0.02em", marginBottom: "12px" }}>
            Analyze your first repository
          </h2>
          <p style={{ fontSize: "14px", color: C.muted, marginBottom: "28px" }}>
            No credentials required — use one of the bundled synthetic fixtures, or connect GitHub OAuth
            to analyze a real repo.
          </p>
          <button
            onClick={() => navigate("/auth")}
            className="px-8 py-3 rounded-xl text-sm font-semibold cursor-pointer"
            style={{ backgroundColor: C.lavender, color: "#ffffff", border: "none", boxShadow: "0 4px 14px rgba(99,102,241,0.3)" }}
          >
            Get started — it's free →
          </button>
        </div>
      </section>
    </div>
  );
}
