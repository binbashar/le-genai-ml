"use client";

import { useQuery } from "@tanstack/react-query";
import type { Agent } from "@/types";

interface AgentsResponse {
  agents: Agent[];
  warning?: string;
}

async function fetchAgents(): Promise<AgentsResponse> {
  const response = await fetch("/api/agents");

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "Failed to fetch agents");
  }

  return response.json();
}

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: fetchAgents,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
}
