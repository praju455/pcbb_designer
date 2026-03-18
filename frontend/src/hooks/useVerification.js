import { useMemo } from "react";

export function useVerification(job) {
  return useMemo(() => job?.verification || { confidence_score: 0, rounds_taken: 0, issues_found: [], issues_fixed: [] }, [job]);
}
