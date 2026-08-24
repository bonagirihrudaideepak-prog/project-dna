import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";

export function useTimeline(snapshotId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.timeline(snapshotId),
    queryFn: () => api.timeline(snapshotId ?? ""),
    enabled: !!snapshotId,
    staleTime: 30_000,
    retry: 1,
  });
}
