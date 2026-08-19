import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Project } from "../lib/types";

export function useProjects(userId?: string) {
  const { data, isLoading, isError, error } = useQuery<Project[]>({
    queryKey: ["projects", userId],
    queryFn: () => api.projects(),
    enabled: !!userId,
    staleTime: 30_000,
    retry: 1,
  });

  return {
    projects: data ?? [],
    isLoading,
    isError,
    error: error as Error | null,
  };
}