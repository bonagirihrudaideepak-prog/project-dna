import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { C, FONT_MONO } from "../lib/ui";
import type { User } from "../lib/types";

const nav = [
  { to: "/", label: "Dashboard", exact: true },
  { to: "/projects", label: "Projects" },
  { to: "/dna", label: "DNA Analysis" },
  { to: "/graph", label: "Graph" },
  { to: "/timeline", label: "Timeline" },
  { to: "/compare", label: "Compare" },
  { to: "/decisions", label: "Decisions" },
  { to: "/experiments", label: "Experiments" },
  { to: "/exports", label: "Exports" },
  { to: "/methodology", label: "Methodology" },
];

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span
      className="flex items-center justify-center rounded-lg flex-shrink-0"
      style={{ width: size, height: size, background: "linear-gradient(135deg, #6366f1 0%, #a78bfa 100%)" }}
    >
      <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 14 14" fill="none">
        <circle cx="4" cy="4" r="2.5" fill="white" />
        <circle cx="10" cy="4" r="1.5" fill="white" fillOpacity="0.6" />
        <circle cx="4" cy="10" r="1.5" fill="white" fillOpacity="0.6" />
        <circle cx="10" cy="10" r="2.5" fill="white" />
        <line x1="4" y1="4" x2="10" y2="10" stroke="white" strokeWidth="1" strokeOpacity="0.5" />
        <line x1="10" y1="4" x2="4" y2="10" stroke="white" strokeWidth="1" strokeOpacity="0.3" />
      </svg>
    </span>
  );
}

export default function NavMenu({ user }: { user: User | null }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const logout = async () => {
    await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
    window.location.href = "/";
  };

  const initials = user
    ? (user.display_name ?? user.login)
        .split(/[\s._-]+/)
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  return (
    <header className="sticky top-0 z-50" style={{ borderBottom: `1px solid ${C.border}`, backgroundColor: C.white }}>
      <div className="max-w-screen-xl mx-auto px-6 flex items-center justify-between h-14">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 no-underline">
          <Logo />
          <span style={{ fontWeight: 700, fontSize: "15px", color: C.ink, letterSpacing: "-0.02em" }}>
            Project DNA
          </span>
        </NavLink>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              style={({ isActive }) => ({
                padding: "4px 12px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 500,
                textDecoration: "none",
                color: isActive ? C.lavender : C.muted,
                backgroundColor: isActive ? C.lavenderSoft : "transparent",
                transition: "all 0.15s",
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {user && (
            <div
              className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ backgroundColor: C.pageBg, border: `1px solid ${C.border}` }}
            >
              <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>{user.login}</span>
              <span
                title="GitHub connected"
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  backgroundColor: user.github_connected ? C.success : C.warning,
                  display: "inline-block",
                }}
              />
            </div>
          )}
          <NavLink
            to="/auth"
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: C.lavender,
              textDecoration: "none",
              padding: "5px 12px",
              borderRadius: "6px",
              border: `1px solid ${C.lavenderMuted}`,
              backgroundColor: C.lavenderSoft,
            }}
          >
            + Analyze
          </NavLink>
          {user ? (
            <>
              <button
                onClick={() => void logout()}
                className="hidden md:block cursor-pointer"
                style={{
                  fontSize: "13px",
                  fontWeight: 500,
                  color: C.muted,
                  background: "none",
                  border: "none",
                  padding: "5px 10px",
                  borderRadius: "6px",
                }}
              >
                Sign out
              </button>
              <div
                className="w-8 h-8 rounded-full hidden md:flex items-center justify-center text-white text-xs font-semibold"
                style={{ background: "linear-gradient(135deg, #6366f1 0%, #a78bfa 100%)", flexShrink: 0 }}
                title={user.login}
              >
                {initials}
              </div>
            </>
          ) : (
            <button
              onClick={() => navigate("/login")}
              className="hidden md:block cursor-pointer"
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: C.muted,
                background: "none",
                border: "none",
                padding: "5px 10px",
                borderRadius: "6px",
              }}
            >
              Sign in
            </button>
          )}
          {/* Mobile hamburger */}
          <button className="md:hidden p-1 cursor-pointer" onClick={() => setOpen(!open)} style={{ color: C.muted }} aria-label="Toggle navigation" aria-expanded={open}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              {open ? (
                <path d="M4 4L16 16M16 4L4 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              ) : (
                <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      {open && (
        <div className="md:hidden px-6 pb-4 flex flex-col gap-1" style={{ backgroundColor: C.white, borderTop: `1px solid ${C.borderLight}` }}>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              onClick={() => setOpen(false)}
              style={({ isActive }) => ({
                padding: "8px 12px",
                borderRadius: "6px",
                fontSize: "14px",
                fontWeight: 500,
                textDecoration: "none",
                color: isActive ? C.lavender : C.muted,
                backgroundColor: isActive ? C.lavenderSoft : "transparent",
              })}
            >
              {item.label}
            </NavLink>
          ))}
          {!user && (
            <NavLink
              to="/login"
              onClick={() => setOpen(false)}
              style={{ padding: "8px 12px", fontSize: "14px", fontWeight: 500, textDecoration: "none", color: C.muted }}
            >
              Sign in
            </NavLink>
          )}
        </div>
      )}
    </header>
  );
}
