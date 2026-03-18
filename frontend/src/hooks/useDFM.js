import { useMutation } from "@tanstack/react-query";
import { validatePCB } from "../api/client";

export function useDFM() {
  return useMutation({
    mutationFn: ({ filePath, fabTarget }) => validatePCB(filePath, fabTarget)
  });
}
