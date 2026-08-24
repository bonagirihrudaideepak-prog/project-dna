import { useNavigate } from "react-router-dom";
import { Logo } from "../components/NavMenu";
import { C, FONT_MONO } from "../lib/ui";

export default function LoginPage() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        backgroundColor: "#f8fafc",
        backgroundImage:
          "radial-gradient(circle at 20% 20%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(236,72,153,0.05) 0%, transparent 50%)",
      }}
    >
      {/* Left decorative panel — hidden on mobile */}
      <div
        className="hidden lg:flex flex-col justify-between p-10"
        style={{
          width: "420px",
          flexShrink: 0,
          background: "linear-gradient(160deg, #6366f1 0%, #a78bfa 60%, #ec4899 100%)",
          color: "#ffffff",
        }}
      >
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-8 h-8 rounded-xl" style={{ backgroundColor: "rgba(255,255,255,0.2)" }}>
            <svg width="16" height="16" viewBox="0 0 14 14" fill="none">
              <circle cx="4" cy="4" r="2.5" fill="white" />
              <circle cx="10" cy="4" r="1.5" fill="white" fillOpacity="0.6" />
              <circle cx="4" cy="10" r="1.5" fill="white" fillOpacity="0.6" />
              <circle cx="10" cy="10" r="2.5" fill="white" />
              <line x1="4" y1="4" x2="10" y2="10" stroke="white" strokeWidth="1" strokeOpacity="0.5" />
            </svg>
          </span>
          <span style={{ fontWeight: 800, fontSize: "16px", letterSpacing: "-0.02em" }}>Project DNA</span>
        </div>

        <div>
          <blockquote style={{ fontSize: "20px", fontWeight: 700, lineHeight: 1.4, marginBottom: "20px", letterSpacing: "-0.01em" }}>
            "Understand not just what your codebase looks like — but how it got there."
          </blockquote>
          <div style={{ fontSize: "13px", opacity: 0.7 }}>Software archaeology, reconstructed from evidence</div>
        </div>

        <div className="space-y-3">
          {[
            { value: "8", label: "DNA dimensions" },
            { value: "100%", label: "evidence-backed scores" },
            { value: "JSON", label: "+ HTML report exports" },
          ].map((s) => (
            <div key={s.label} className="flex items-center gap-3">
              <span style={{ fontFamily: FONT_MONO, fontSize: "20px", fontWeight: 800 }}>{s.value}</span>
              <span style={{ fontSize: "13px", opacity: 0.7 }}>{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div style={{ width: "100%", maxWidth: "400px" }}>
          <div className="flex items-center justify-center gap-2 mb-8">
            <Logo size={32} />
            <span style={{ fontWeight: 800, fontSize: "17px", color: C.ink, letterSpacing: "-0.03em" }}>Project DNA</span>
          </div>

          {/* GitHub OAuth button */}
          <button
            onClick={() => (window.location.href = "/api/v1/auth/github/start")}
            className="w-full flex items-center justify-center gap-3 py-3 rounded-xl mb-5 text-sm font-semibold transition-all cursor-pointer"
            style={{
              backgroundColor: "#1e293b",
              color: "#ffffff",
              border: "none",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
              <path fillRule="evenodd" clipRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" fill="currentColor" />
            </svg>
            Continue with GitHub
          </button>

          <p style={{ fontSize: "13px", color: C.muted, textAlign: "center", lineHeight: 1.7, marginBottom: "24px" }}>
            Authentication is GitHub OAuth only — your account scopes what Project DNA can see.
            After signing in you can analyze your repositories or explore the bundled synthetic fixtures.
          </p>

          <button
            onClick={() => navigate("/landing")}
            className="w-full py-2.5 rounded-xl text-sm font-semibold cursor-pointer"
            style={{
              backgroundColor: C.lavenderSoft,
              color: C.lavender,
              border: `1px solid ${C.lavenderMuted}`,
            }}
          >
            ← Back to overview
          </button>
        </div>
      </div>
    </div>
  );
}
