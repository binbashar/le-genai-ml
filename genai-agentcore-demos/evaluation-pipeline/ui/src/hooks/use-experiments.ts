"use client";

import { useQuery } from "@tanstack/react-query";
import type { ExperimentSummary } from "@/types";

interface ExperimentsResponse {
    executions: ExperimentSummary[];
}

async function fetchExperiments(): Promise<ExperimentSummary[]> {
    const response = await fetch("/api/experiments");
    if (!response.ok) {
        throw new Error("Failed to fetch experiments");
    }
    const data: ExperimentsResponse = await response.json();
    return data.executions;
}

export function useExperiments() {
    return useQuery({
        queryKey: ["experiments"],
        queryFn: fetchExperiments,
        refetchInterval: 30000, // Refetch every 30 seconds
    });
}
