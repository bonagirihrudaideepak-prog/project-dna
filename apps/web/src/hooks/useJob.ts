import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AnalysisJob } from "../lib/types";

export function useJob(jobId: string | null, onDone?: () => void) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const j = await api.job(jobId);
        if (cancelled) return;
        setJob(j);
        if (["COMPLETED", "FAILED", "CANCELLED"].includes(j.state)) {
          if (j.state === "COMPLETED") onDone?.();
          if (j.state === "FAILED") setError(j.error_detail || "Analysis failed");
          return;
        }
        setTimeout(tick, 1500);
      } catch (e) {
        if (!cancelled) {
          setError(String(e));
          setTimeout(tick, 3000);
        }
      }
    };
    tick();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return { job, error };
}

export function useSnapshotId(projectId: string | undefined) {
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    api
      .snapshots(projectId)
      .then((snaps) => {
        const completed = snaps.find((s) => s.status === "COMPLETED");
        setSnapshotId(completed?.id ?? snaps[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  return { snapshotId, loading };
}