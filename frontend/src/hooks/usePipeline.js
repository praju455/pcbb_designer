import { useMutation, useQuery } from "@tanstack/react-query";
import { generatePCB, getJobStatus } from "../api/client";

export function usePipeline(jobId) {
  const generateMutation = useMutation({
    mutationFn: ({ description, options }) => generatePCB(description, options)
  });

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJobStatus(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (query) => (["done", "error"].includes(query?.state?.data?.status) ? false : 2000)
  });

  return { generateMutation, jobQuery };
}
