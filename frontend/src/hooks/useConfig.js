import { useMutation, useQuery } from "@tanstack/react-query";
import { getConfig, getHealth, updateConfig } from "../api/client";

export function useConfig() {
  const configQuery = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 5000 });
  const updateMutation = useMutation({ mutationFn: updateConfig });
  return { configQuery, healthQuery, updateMutation };
}
