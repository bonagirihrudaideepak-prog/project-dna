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
    retry: 0,
    // A signed-out production user would otherwise re-401 on every focus.
    refetchOnWindowFocus: false,
  });

  const status = (error as (Error & { status?: number }) | null)?.status;

  return {
    projects: data ?? [],
    isLoading,
    isError,
    /** True when the backend requires sign-in for this listing. */
    authRequired: isError && status === 401,
    error: error as Error | null,
    refetch,
  };
}
