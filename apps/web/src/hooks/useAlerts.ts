import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queryKeys";
import type { Alert, AlertRule } from "../lib/types";

export function useAlerts() {
  return useQuery<Alert[]>({
    queryKey: queryKeys.alerts(),
    queryFn: () => api.alerts(),
    staleTime: 30_000,
  });
}

export function useAlertRules(projectId: string | undefined) {
  return useQuery<AlertRule[]>({
    queryKey: queryKeys.alertRules(projectId),
    queryFn: () => api.alertRules(projectId ?? ""),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export interface CreateAlertRuleInput {
  dimension: string;
  operator: "lt" | "gt";
  threshold: number;
}

export function useCreateAlertRule(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAlertRuleInput) => {
      if (!projectId) throw new Error("No project selected");
      return api.createAlertRule(projectId, input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alertRules(projectId) });
      // A new rule changes which alerts belong to this project's feed.
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts() });
    },
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => api.acknowledgeAlert(alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.alerts() }),
  });
}

export function useDeleteAlertRule(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => api.deleteAlertRule(projectId, ruleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.alertRules(projectId) }),
  });
}
