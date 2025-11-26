"use client";

import { useQuery } from "@tanstack/react-query";
import { POLLING_INTERVAL_MS } from "@/lib/constants";
import { isTerminalState } from "@/types";
import type { ExperimentStatusResponse } from "@/types";

async function fetchExperimentStatus(
  executionArn: string
): Promise<ExperimentStatusResponse> {
  const encodedArn = encodeURIComponent(executionArn);
  const response = await fetch(`/api/experiments/${encodedArn}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "Failed to fetch experiment status");
  }

  return response.json();
}

export function useExperimentStatus(executionArn: string | null) {
  return useQuery({
    queryKey: ["experiment", executionArn],
    queryFn: () => fetchExperimentStatus(executionArn!),
    enabled: !!executionArn,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling when execution reaches a terminal state
      if (status && isTerminalState(status)) {
        return false;
      }

      // Exponential backoff: 3s * 1.5^attempts, capped at 30s
      const attempts = query.state.dataUpdateCount;
      const backoff = Math.min(
        POLLING_INTERVAL_MS * Math.pow(1.5, attempts),
        30000
      );
      return backoff;
    },
    refetchOnWindowFocus: false,
    retry: 3,
  });
}
