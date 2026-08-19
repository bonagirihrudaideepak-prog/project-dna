import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { AnalysisJob } from "../lib/types";

export function useJob(jobId: string | null, onDone?: () => void) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      try {
        const j = await api.job(jobId);
        if (cancelled) return;
        setJob(j);
        if (["COMPLETED", "FAILED", "CANCELLED"].includes(j.state)) {
          if (j.state === "COMPLETED") onDoneRef.current?.();
          if (j.state === "FAILED") setError(j.error_detail || "Analysis failed");
          return;
        }
        timer = setTimeout(tick, 1500);
      } catch (e) {
        if (!cancelled) {
          setError(String(e));
          timer = setTimeout(tick, 3000);
        }
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  return { job, error };
}

export function useSnapshotId(projectId: string | undefined) {
  const { data: snaps, isLoading } = useQuery({
    queryKey: ["snapshots", projectId],
    queryFn: () => api.snapshots(projectId!),
    enabled: !!projectId,
  });
  const completed = snaps?.find((s) => s.status === "COMPLETED");
  return { snapshotId: completed?.id ?? snaps?.[0]?.id ?? null, loading: isLoading };
}