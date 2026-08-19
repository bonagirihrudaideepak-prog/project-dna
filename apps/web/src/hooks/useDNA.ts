import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { DNAScore } from "../lib/types";

export function useDNA(snapshotId: string | undefined) {
  return useQuery<DNAScore[]>({
    queryKey: ["analysis", snapshotId],
    queryFn: () => api.dna(snapshotId ?? ""),
    enabled: !!snapshotId,
    staleTime: 30_000,
    retry: 1,
  });
}