import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Methodology } from "../lib/types";

export function useMethodology() {
  return useQuery<Methodology>({
    queryKey: ["methodology"],
    queryFn: () => api.methodology(),
    staleTime: 300_000,
    retry: 1,
  });
}
