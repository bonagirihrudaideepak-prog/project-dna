import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Logo } from "../components/NavMenu";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { useJob } from "../hooks/useJob";
import { C, FONT_MONO } from "../lib/ui";
import type { GitHubRepo, Project } from "../lib/types";

type Step = "connect" | "select-repo" | "analyzing";

const DIM_TICKS = ["Maintainability", "Testing", "Docs", "Evolution", "Delivery", "Scalability", "Complexity", "Debt"];

function GitHubIcon({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path fillRule="evenodd" clipRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" fill="currentColor" />
    </svg>
  );
}

export default function AuthPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("connect");
  const [repoInput, setRepoInput] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const queuedProjectRef = useRef<string | null>(null);

  // Signed-in users skip Connect; anonymous users must OAuth first.
  const { data: user } = useQuery({
    queryKey: queryKeys.me(),
    queryFn: api.me,
    retry: false,
    staleTime: 60_000,
  });
  const { data: projects } = useQuery<Project[]>({
    queryKey: queryKeys.projects(user?.id ?? null),
    queryFn: api.projects,
    enabled: !!user,
    staleTime: 30_000,
    retry: 0,
  });
  const { data: ghRepos } = useQuery<GitHubRepo[]>({
    queryKey: ["github-repos", ""],
    queryFn: () => api.githubRepositories(""),
    enabled: !!user,
    staleTime: 60_000,
    retry: false,
  });

  const fixtures = useMemo(() => (projects ?? []).filter((p) => p.is_fixture), [projects]);
  const importedNames = useMemo(() => new Set((projects ?? []).map((p) => p.full_name)), [projects]);

  const filteredRepos = useMemo(() => {
    const q = repoInput.trim().toLowerCase();
    return (ghRepos ?? []).filter(
      (r) =>
        !q ||
        r.full_name.toLowerCase().includes(q) ||
        (r.description ?? "").toLowerCase().includes(q)
    );
  }, [ghRepos, repoInput]);

  const { job, error: jobError } = useJob(jobId, () => {
    if (queuedProjectRef.current) navigate(`/dna?project=${queuedProjectRef.current}`);
  });

  useEffect(() => {
    if (user && step === "connect") setStep("select-repo");
    if (!user && step !== "connect") setStep("connect");
  }, [user, step]);

  const queueFor = async (projectId: string) => {
    setStartError(null);
    try {
      const j = await api.queueAnalysis(projectId);
      queuedProjectRef.current = projectId;
      setStep("analyzing");
      setJobId(j.id);
    } catch (e) {
      setStartError((e as Error).message);
    }
  };

  const startGithubAnalysis = async (repo: GitHubRepo) => {
    setStartError(null);
    try {
      const project = await api.importProject(repo.full_name, repo.default_branch);
      await queueFor(project.id);
    } catch (e) {
      setStartError(`${repo.full_name}: ${(e as Error).message}`);
    }
  };

  const progress = job?.progress ?? 0;

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f8fafc", display: "flex", flexDirection: "column" }}>
      {/* Mini header */}
      <header style={{ borderBottom: `1px solid ${C.border}`, backgroundColor: "#ffffff" }}>
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          <button onClick={() => navigate("/landing")} className="flex items-center gap-2 cursor-pointer" style={{ background: "none", border: "none" }}>
            <Logo />
            <span style={{ fontWeight: 700, fontSize: "15px", color: C.ink, letterSpacing: "-0.02em" }}>Project DNA</span>
          </button>
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            {(["connect", "select-repo", "analyzing"] as Step[]).map((s, i) => {
              const order = ["connect", "select-repo", "analyzing"];
              const done = order.indexOf(step) > i;
              const active = step === s;
              return (
                <div key={s} className="flex items-center gap-2">
                  <div
                    style={{
                      width: "22px",
                      height: "22px",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: done ? "#10b981" : active ? C.lavender : "#f1f5f9",
                      fontSize: "11px",
                      fontWeight: 700,
                      color: done || active ? "#ffffff" : C.faint,
                    }}
                  >
                    {done ? "✓" : i + 1}
                  </div>
                  {i < 2 && <div style={{ width: "24px", height: "1px", backgroundColor: done ? "#10b981" : "#e2e8f0" }} />}
                </div>
              );
            })}
          </div>
        </div>
      </header>

      <div className="flex-1 flex items-start justify-center px-6 py-12">
        <div style={{ width: "100%", maxWidth: "560px" }}>
          {/* ── Step 1: Connect ── */}
          {step === "connect" && !user && (
            <div className="text-center" style={{ paddingTop: 40 }}>
              <h1 style={{ fontSize: "24px", fontWeight: 800, color: C.ink, letterSpacing: "-0.02em", marginBottom: "8px" }}>
                Analyze a repository
              </h1>
              <p style={{ fontSize: "13px", color: C.muted, marginBottom: "28px" }}>
                Project DNA uses GitHub OAuth — sign in to import repositories or explore bundled fixtures.
              </p>

              <button
                onClick={() => (window.location.href = "/api/v1/auth/github/start")}
                className="w-full flex items-center gap-4 p-4 rounded-xl text-left transition-all cursor-pointer"
                style={{ backgroundColor: "#1e293b", border: "2px solid #1e293b", color: "#ffffff" }}
              >
                <GitHubIcon />
                <div>
                  <div style={{ fontSize: "14px", fontWeight: 600 }}>Continue with GitHub</div>
                  <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "2px" }}>read:user + repo scope — OAuth 2.0</div>
                </div>
                <svg style={{ marginLeft: "auto" }} width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M4 7h6M8 5l2 2-2 2" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>

              <button
                onClick={() => navigate("/landing")}
                style={{
                  marginTop: "20px",
                  fontSize: "12px",
                  color: C.faint,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                ← Back to overview
              </button>
            </div>
          )}

          {/* ── Step 2: Select repo ── */}
          {step === "select-repo" && user && (
            <div>
              <h1 style={{ fontSize: "22px", fontWeight: 800, color: C.ink, letterSpacing: "-0.02em", marginBottom: "8px" }}>
                Choose what to analyze
              </h1>
              <p style={{ fontSize: "13px", color: C.muted, marginBottom: "24px" }}>
                Pick one of your GitHub repositories, or run analysis on a bundled synthetic fixture.
              </p>

              {(startError || jobError) && (
                <div className="rounded-lg p-3 mb-4" style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", fontSize: "12px", color: "#7f1d1d" }}>
                  {startError ?? jobError}
                </div>
              )}

              {/* Fixtures */}
              {fixtures.length > 0 && (
                <>
                  <div style={{ fontSize: "11px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                    Synthetic fixtures
                  </div>
                  <div className="space-y-3 mb-6">
                    {fixtures.map((f) => (
                      <button
                        key={f.id}
                        onClick={() => void queueFor(f.id)}
                        className="w-full flex items-center gap-4 p-4 rounded-xl text-left cursor-pointer transition-all"
                        style={{
                          backgroundColor: "#ffffff",
                          border: `2px solid ${C.border}`,
                        }}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span style={{ fontFamily: FONT_MONO, fontSize: "13px", fontWeight: 600, color: C.ink }}>{f.full_name}</span>
                            <span style={{ fontFamily: FONT_MONO, fontSize: "10px", color: C.faint, backgroundColor: C.borderLight, padding: "1px 6px", borderRadius: "3px" }}>
                              fixture
                            </span>
                          </div>
                          <p style={{ fontSize: "12px", color: C.muted, marginBottom: 0 }} className="truncate">
                            {f.description ?? "Bundled synthetic repository"}
                          </p>
                        </div>
                        <span style={{ fontFamily: FONT_MONO, fontSize: "12px", fontWeight: 600, color: C.lavender, flexShrink: 0 }}>Run →</span>
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-3 mb-6">
                    <div style={{ flex: 1, height: "1px", backgroundColor: "#e2e8f0" }} />
                    <span style={{ fontSize: "12px", color: C.faint }}>or pick a GitHub repository</span>
                    <div style={{ flex: 1, height: "1px", backgroundColor: "#e2e8f0" }} />
                  </div>
                </>
              )}

              {/* GitHub repos */}
              <input
                value={repoInput}
                onChange={(e) => setRepoInput(e.target.value)}
                placeholder="Filter your repositories…"
                aria-label="Filter repositories"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  fontFamily: FONT_MONO,
                  fontSize: "13px",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: `1px solid ${C.border}`,
                  outline: "none",
                  marginBottom: "12px",
                }}
              />
              <div className="space-y-2" style={{ maxHeight: 320, overflowY: "auto" }}>
                {filteredRepos.map((r) => (
                  <div
                    key={r.github_repo_id ?? r.full_name}
                    className="w-full flex items-center gap-4 p-3 rounded-xl"
                    style={{ backgroundColor: "#ffffff", border: `1px solid ${C.border}` }}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <GitHubIcon size={14} />
                        <span style={{ fontFamily: FONT_MONO, fontSize: "12px", fontWeight: 600, color: C.ink }}>{r.full_name}</span>
                        {importedNames.has(r.full_name) && (
                          <span style={{ fontSize: "10px", backgroundColor: "#d1fae5", color: "#065f46", padding: "1px 6px", borderRadius: "3px" }}>imported</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => void startGithubAnalysis(r)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer flex-shrink-0"
                      style={{ backgroundColor: C.lavender, color: "#ffffff", border: "none" }}
                    >
                      Analyze
                    </button>
                  </div>
                ))}
                {filteredRepos.length === 0 && (
                  <p style={{ fontSize: "12px", color: C.faint }}>No repositories matched.</p>
                )}
              </div>
            </div>
          )}

          {/* ── Step 3: Analyzing ── */}
          {step === "analyzing" && (
            <div className="text-center">
              <div
                className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-6"
                style={{ background: "linear-gradient(135deg, #6366f1 0%, #a78bfa 100%)" }}
              >
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                  <circle cx="8" cy="8" r="5" fill="white" />
                  <circle cx="20" cy="8" r="3" fill="white" fillOpacity="0.5" />
                  <circle cx="8" cy="20" r="3" fill="white" fillOpacity="0.5" />
                  <circle cx="20" cy="20" r="5" fill="white" />
                  <line x1="8" y1="8" x2="20" y2="20" stroke="white" strokeWidth="1.5" strokeOpacity="0.4" />
                  <line x1="20" y1="8" x2="8" y2="20" stroke="white" strokeWidth="1.5" strokeOpacity="0.25" />
                </svg>
              </div>

              <h1 style={{ fontSize: "22px", fontWeight: 800, color: C.ink, letterSpacing: "-0.02em", marginBottom: "8px" }}>
                Analyzing DNA…
              </h1>
              <p style={{ fontSize: "13px", color: C.muted, marginBottom: "32px" }}>{job?.phase ?? "Initializing…"}</p>

              {/* Progress bar */}
              <div className="rounded-full overflow-hidden mb-3" style={{ height: "8px", backgroundColor: "#f1f5f9" }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${progress}%`, background: "linear-gradient(90deg, #6366f1, #a78bfa)", transition: "width 0.5s ease" }}
                />
              </div>
              <div style={{ fontFamily: FONT_MONO, fontSize: "12px", color: C.faint }}>{progress}%</div>

              {/* Dimension ticks */}
              <div className="grid grid-cols-4 gap-2 mt-8">
                {DIM_TICKS.map((dim, i) => {
                  const done = progress > (i + 1) * 11;
                  return (
                    <div
                      key={dim}
                      className="py-2 px-2 rounded-lg text-center"
                      style={{ backgroundColor: done ? C.lavenderSoft : "#f8fafc", border: `1px solid ${done ? C.lavenderMuted : "#f1f5f9"}` }}
                    >
                      <div style={{ fontSize: "9px", color: done ? C.lavender : C.faint, fontWeight: done ? 600 : 400 }}>{dim}</div>
                      {done && <div style={{ fontSize: "9px", color: "#10b981" }}>✓</div>}
                    </div>
                  );
                })}
              </div>

              {jobError && (
                <div className="rounded-lg p-3 mt-6" style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", fontSize: "12px", color: "#7f1d1d" }}>
                  {jobError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
