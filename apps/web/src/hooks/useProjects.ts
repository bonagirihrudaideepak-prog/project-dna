import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import type { Project } from "../lib/types";

export function useProjects(userId?: string, options?: { enabled?: boolean }) {
  const { data, isLoading, isError, error, refetch } = useQuery<Project[]>({
    queryKey: queryKeys.projects(userId),
    queryFn: () => api.projects(),
    // Default: wait for a known user (avoids a wasted pre-auth fetch).
    // Callers fetching anonymously pass { enabled: true }.
    enabled: options?.enabled ?? !!userId,
    staleTime: 30_000,
    retry: 1,
  });

  return {
    projects: data ?? [],
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
  };
}
