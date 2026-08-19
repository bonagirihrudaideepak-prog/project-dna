import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useComparison(
  snapshotA: string,
  snapshotB: string,
) {
  return useQuery({
    queryKey: ["comparison", snapshotA, snapshotB],
    queryFn: () => api.compare(snapshotA, snapshotB),
    enabled: !!snapshotA && !!snapshotB,
    staleTime: 60_000,
  });
}