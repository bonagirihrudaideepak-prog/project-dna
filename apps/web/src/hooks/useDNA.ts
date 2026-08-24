import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import type { DNAScore } from "../lib/types";

export function useDNA(snapshotId: string | null | undefined) {
  return useQuery<DNAScore[]>({
    queryKey: queryKeys.analysis(snapshotId),
    queryFn: () => api.dna(snapshotId ?? ""),
    enabled: !!snapshotId,
    staleTime: 30_000,
    retry: 1,
  });
}
