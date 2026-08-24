import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TrendPoint } from "../lib/types";

export function useTrends(projectId: string | undefined) {
  return useQuery<TrendPoint[]>({
    queryKey: ["trends", projectId],
    queryFn: () => api.trends(projectId ?? ""),
    enabled: !!projectId,
    staleTime: 60_000,
    retry: 1,
  });
}