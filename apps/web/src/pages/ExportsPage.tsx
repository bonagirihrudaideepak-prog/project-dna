import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, ProjectSelector, useUserAndProjects } from "../components/ProjectSelector";
import { LoadingState, EmptyState } from "../components/StateViews";
import { useActiveProject } from "../hooks/useActiveProject";
import { useSnapshotId } from "../hooks/useJob";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import { C, FONT_MONO, panelStyle } from "../lib/ui";

type Format = "json" | "html";

const FMT_META: Record<Format, { chipBg: string; chipText: string; title: string; desc: string }> = {
  json: { chipBg: "#dbeafe", chipText: "#1e40af", title: "JSON", desc: "Structured — full snapshot for API & automation" },
  html: { chipBg: "#ede9f2", chipText: "#4338ca", title: "HTML report", desc: "Print-friendly — for vivas, wikis and reports" },
};

interface ExportArtifact {
  name: string;
  size: string;
  ago: string;
  fmt: Format;
}

function sizeLabel(bytes: number) {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}

export default function ExportsPage() {
  const { user, projects, loading } = useUserAndProjects();
  const { projectId, setActive, project } = useActiveProject(projects);
  const { snapshotId, loading: snapLoading } = useSnapshotId(projectId);
  const [format, setFormat] = useState<Format>("json");
  const [payload, setPayload] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [history, setHistory] = useState<ExportArtifact[]>([]);

  const { data: projDetail } = useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => api.project(projectId!),
    enabled: !!projectId,
  });

  const generate = useCallback(async () => {
    if (!snapshotId) return;
    setError(null);
    setBusy(true);
    try {
      if (format === "json") {
        const res = await api.exportJson(snapshotId);
        const text = typeof res === "string" ? res : JSON.stringify(res, null, 2);
        setPayload(text);
        return text;
      }
      const text = await api.exportHtml(snapshotId);
      setPayload(text);
      return text;
    } catch (e) {
      setError((e as Error).message);
      setPayload(null);
      return null;
    } finally {
      setBusy(false);
    }
  }, [format, snapshotId]);

  const download = useCallback(
    async (artifactName?: string) => {
      let text = payload ?? (await generate());
      if (!text) return;
      const mime = format === "json" ? "application/json" : "text/html";
      const ext = format === "json" ? "json" : "html";
      const base = (projDetail?.full_name ?? project?.full_name ?? "project").replace("/", "-");
      const name =
        artifactName ??
        `${base}-dna-${new Date().toISOString().slice(0, 10)}.${ext}`;
      const blob = new Blob([text], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setHistory((h) => [
        {
          name,
          size: sizeLabel(new TextEncoder().encode(text).length),
          ago: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          fmt: format,
        },
        ...h.slice(0, 4),
      ]);
    },
    [payload, generate, format, projDetail, project]
  );

  const copy = useCallback(async () => {
    try {
      let text = payload ?? (await generate());
      if (!text) return;
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
    setTimeout(() => setCopyState("idle"), 2500);
  }, [payload, generate]);

  const byteSize = useMemo(() => (payload ? new TextEncoder().encode(payload).length : 0), [payload]);
  const lineCount = useMemo(() => (payload && format === "json" ? payload.split("\n").length : null), [payload, format]);

  if (loading || snapLoading) return <LoadingState />;

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader title="Exports" subtitle="Download analysis results as structured JSON or a printable HTML report" />

      {!user || projects.length === 0 ? (
        <EmptyState>
          Run an analysis first — exports are generated from a completed snapshot.
        </EmptyState>
      ) : !snapshotId ? (
        <EmptyState>No completed snapshot to export for this repository yet.</EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          {/* ── Left panel ── */}
          <div className="lg:col-span-2 space-y-4">
            {/* Repo */}
            <div className="rounded-xl p-5" style={panelStyle}>
              <h2 style={{ fontSize: "12px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Repository
              </h2>
              <ProjectSelector value={projectId ?? ""} projects={projects} onChange={(id) => { setActive(id); setPayload(null); }} />
              <p style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint, marginTop: "8px", marginBottom: 0 }}>
                snapshot {snapshotId.slice(0, 8)}
                {projDetail?.latest_snapshot?.captured_at
                  ? ` · ${new Date(projDetail.latest_snapshot.captured_at).toLocaleDateString()}`
                  : ""}
              </p>
            </div>

            {/* Format picker */}
            <div className="rounded-xl p-5" style={panelStyle}>
              <h2 style={{ fontSize: "12px", fontWeight: 600, color: C.faint, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Format
              </h2>
              <div className="space-y-2">
                {(Object.keys(FMT_META) as Format[]).map((f) => {
                  const active = format === f;
                  const meta = FMT_META[f];
                  return (
                    <button
                      key={f}
                      onClick={() => { setFormat(f); setPayload(null); }}
                      className="w-full text-left flex items-center gap-3 p-3 rounded-lg transition-all cursor-pointer"
                      style={{
                        border: `1px solid ${active ? C.lavenderMuted : C.borderLight}`,
                        backgroundColor: active ? C.lavenderSoft : C.pageBg,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: FONT_MONO,
                          fontSize: "10px",
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          backgroundColor: active ? C.lavender : "#e2e8f0",
                          color: active ? "#ffffff" : "#64748b",
                          letterSpacing: "0.04em",
                          minWidth: "40px",
                          textAlign: "center",
                        }}
                      >
                        {f.toUpperCase()}
                      </span>
                      <div>
                        <div style={{ fontSize: "13px", fontWeight: 500, color: C.ink }}>{meta.title}</div>
                        <div style={{ fontSize: "11px", color: C.faint }}>{meta.desc}</div>
                      </div>
                      {active && (
                        <svg style={{ marginLeft: "auto", flexShrink: 0 }} width="14" height="14" viewBox="0 0 14 14" fill="none">
                          <path d="M2.5 7l3 3 6-6" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Size indicator */}
            {payload && (
              <div className="flex items-center justify-between px-4 py-3 rounded-lg" style={{ backgroundColor: C.pageBg, border: `1px solid ${C.border}` }}>
                <span style={{ fontSize: "12px", color: C.muted }}>Payload size</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: "12px", fontWeight: 600, color: C.ink }}>{sizeLabel(byteSize)}</span>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-2">
              <button
                onClick={() => void download()}
                disabled={busy}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer"
                style={{
                  backgroundColor: busy ? C.lavenderMuted : C.lavender,
                  color: "#ffffff",
                  border: "none",
                  cursor: busy ? "not-allowed" : "pointer",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M7 2v7M4 7l3 3 3-3M2 11h10" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {busy ? "Generating…" : `Download .${format === "json" ? "json" : "html"}`}
              </button>
              <button
                onClick={() => void copy()}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer"
                style={{
                  backgroundColor: copyState === "copied" ? "#d1fae5" : copyState === "error" ? "#fee2e2" : C.pageBg,
                  color: copyState === "copied" ? "#065f46" : copyState === "error" ? "#7f1d1d" : C.body,
                  border: `1px solid ${copyState === "copied" ? "#a7f3d0" : copyState === "error" ? "#fca5a5" : C.border}`,
                }}
              >
                {copyState === "copied" ? "Copied to clipboard!" : copyState === "error" ? "Copy failed — try again" : "Generate & copy to clipboard"}
              </button>
            </div>

            {error && (
              <div className="rounded-lg p-3" style={{ backgroundColor: "#fee2e2", border: "1px solid #fca5a5", fontSize: "12px", color: "#7f1d1d" }}>
                {error}
              </div>
            )}
          </div>

          {/* ── Preview panel ── */}
          <div className="lg:col-span-3 flex flex-col rounded-xl overflow-hidden" style={{ ...panelStyle, minHeight: "460px" }}>
            <div className="flex items-center justify-between px-4 py-3 flex-shrink-0" style={{ backgroundColor: C.pageBg, borderBottom: `1px solid ${C.border}` }}>
              <div className="flex items-center gap-2">
                <span
                  style={{
                    fontFamily: FONT_MONO,
                    fontSize: "10px",
                    fontWeight: 700,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    backgroundColor: FMT_META[format].chipBg,
                    color: FMT_META[format].chipText,
                  }}
                >
                  {format.toUpperCase()}
                </span>
                <span style={{ fontSize: "12px", color: C.faint }}>Preview</span>
              </div>
              <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: C.faint }}>
                {payload ? (lineCount !== null ? `${lineCount} lines · ${sizeLabel(byteSize)}` : sizeLabel(byteSize)) : "not generated"}
              </span>
            </div>
            {format === "html" && payload ? (
              <iframe title="HTML export preview" srcDoc={payload} style={{ width: "100%", flex: 1, border: "none", background: "#fff", minHeight: 420 }} />
            ) : (
              <pre
                style={{
                  margin: 0,
                  padding: "16px 20px",
                  fontFamily: FONT_MONO,
                  fontSize: "11.5px",
                  lineHeight: 1.75,
                  color: C.body,
                  backgroundColor: "#ffffff",
                  overflowX: "auto",
                  overflowY: "auto",
                  flex: 1,
                  whiteSpace: "pre-wrap",
                }}
              >
                {payload?.slice(0, 8000) ?? "Hit “Download” or “Generate & copy” to render the export here."}
              </pre>
            )}
          </div>

          {/* Session downloads */}
          {history.length > 0 && (
            <div className="mt-6 rounded-xl lg:col-span-5 overflow-hidden" style={panelStyle}>
              <div className="px-5 py-4" style={{ borderBottom: `1px solid ${C.borderLight}` }}>
                <h2 style={{ fontSize: "13px", fontWeight: 600, color: C.ink }}>This session</h2>
              </div>
              <div>
                {history.map((item, i) => (
                  <div
                    key={`${item.name}-${i}`}
                    className="flex items-center gap-4 px-5 py-3"
                    style={{ borderBottom: i < history.length - 1 ? `1px solid ${C.borderLight}` : "none" }}
                  >
                    <span
                      style={{
                        fontFamily: FONT_MONO,
                        fontSize: "10px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: "4px",
                        backgroundColor: FMT_META[item.fmt].chipBg,
                        color: FMT_META[item.fmt].chipText,
                        flexShrink: 0,
                      }}
                    >
                      {item.fmt.toUpperCase()}
                    </span>
                    <span style={{ fontFamily: FONT_MONO, fontSize: "12px", color: C.body, flex: 1, minWidth: 0 }} className="truncate">
                      {item.name}
                    </span>
                    <span style={{ fontSize: "11px", color: C.faint }}>{item.size}</span>
                    <span style={{ fontSize: "11px", color: C.faint, minWidth: "70px", textAlign: "right" }}>{item.ago}</span>
                    <button
                      style={{ fontSize: "12px", color: C.lavender, fontWeight: 500, background: "none", border: "none", cursor: "pointer", padding: 0 }}
                      onClick={() => void download(item.name)}
                    >
                      ↓ Re-download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
