"use client";

import { useMutation } from "@tanstack/react-query";
import { formatDateForAPI } from "@/lib/utils";
import type { ExperimentFormSchema } from "@/lib/schemas";
import type { StartExperimentResponse } from "@/types";

interface StartExperimentInput extends ExperimentFormSchema {}

async function startExperiment(
  input: StartExperimentInput
): Promise<StartExperimentResponse> {
  const response = await fetch("/api/experiments", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      agent_name: input.agentName,
      start_date: formatDateForAPI(input.startDate),
      end_date: formatDateForAPI(input.endDate),
      limit: input.maxLimit,
      metrics: input.metrics,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "Failed to start experiment");
  }

  return response.json();
}

export function useStartExperiment() {
  return useMutation({
    mutationFn: startExperiment,
  });
}
