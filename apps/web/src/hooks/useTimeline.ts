import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useTimeline(snapshotId: string | undefined) {
  return useQuery({
    queryKey: ["timeline", snapshotId],
    queryFn: () => api.timeline(snapshotId ?? ""),
    enabled: !!snapshotId,
    staleTime: 30_000,
    retry: 1,
  });
}