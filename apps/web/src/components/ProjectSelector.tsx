import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { C, FONT_MONO } from "../lib/ui";
import type { Project } from "../lib/types";

/**
 * Repository selector used across global pages (design: "REPOSITORY" input row).
 */
export function ProjectSelector({
  value,
  projects,
  onChange,
  label = "REPOSITORY",
}: {
  value: string;
  projects: Project[];
  onChange: (id: string) => void;
  label?: string;
}) {
  return (
    <div className="flex-1 min-w-48">
      <label style={{ fontSize: "11px", color: C.faint, fontWeight: 500, display: "block", marginBottom: "4px" }}>
        {label}
      </label>
      <select
        aria-label="Select project"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          boxSizing: "border-box",
          fontFamily: FONT_MONO,
          fontSize: "13px",
          border: `1px solid ${C.border}`,
          borderRadius: "8px",
          padding: "8px 12px",
          color: C.ink,
          backgroundColor: C.white,
          outline: "none",
          cursor: "pointer",
        }}
      >
        {projects.length === 0 && <option value="">No repositories yet</option>}
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.full_name}
            {p.is_fixture ? " (fixture)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Primary button per the design spec. */
export function PrimaryButton({
  children,
  onClick,
  disabled,
  type,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type ?? "button"}
      onClick={onClick}
      disabled={disabled}
      className="px-5 py-2 rounded-lg font-medium text-sm transition-all cursor-pointer"
      style={{
        backgroundColor: disabled ? C.lavenderMuted : C.lavender,
        color: C.white,
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {children}
    </button>
  );
}

/** Ghost/secondary button per the design spec. */
export function GhostButton({
  children,
  onClick,
  disabled,
  type,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type ?? "button"}
      onClick={onClick}
      disabled={disabled}
      className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
      style={{
        backgroundColor: C.white,
        color: C.lavender,
        border: `1px solid ${C.lavenderMuted}`,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {children}
    </button>
  );
}

/** Standard page header block. */
export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-6">
      <h1 style={{ fontSize: "22px", fontWeight: 700, color: C.ink, letterSpacing: "-0.02em" }}>{title}</h1>
      <p style={{ fontSize: "13px", color: C.muted, marginTop: "4px" }}>{subtitle}</p>
    </div>
  );
}

/**
 * Loads the signed-in user + project list; the common data spine of every
 * global page. Anonymous visitors get an empty (but valid) project list.
 */
export function useUserAndProjects() {
  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: queryKeys.me(),
    queryFn: api.me,
    retry: false,
    staleTime: 60_000,
  });
  const { data: projects, isLoading: projectsLoading } = useQuery<Project[]>({
    queryKey: queryKeys.projects(user?.id ?? null),
    queryFn: api.projects,
    enabled: !!user,
    staleTime: 30_000,
    retry: 0,
    refetchOnWindowFocus: false,
  });
  return {
    user: user ?? null,
    projects: projects ?? [],
    loading: userLoading || (!!user && projectsLoading),
  };
}
