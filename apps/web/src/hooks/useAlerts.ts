import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Alert, AlertRule } from "../lib/types";

export function useAlerts() {
  return useQuery<Alert[]>({
    queryKey: ["alerts"],
    queryFn: () => api.alerts(),
    staleTime: 30_000,
  });
}

export function useAlertRules(projectId: string | undefined) {
  return useQuery<AlertRule[]>({
    queryKey: ["alert-rules", projectId],
    queryFn: () => api.alertRules(projectId ?? ""),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => api.acknowledgeAlert(alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });
}

export function useDeleteAlertRule(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => api.deleteAlertRule(projectId, ruleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules", projectId] }),
  });
}