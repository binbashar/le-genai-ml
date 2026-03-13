"use client";

import { cn } from "@/lib/utils";
import type { Agent } from "@/types";

interface AgentSelectorProps {
  agents: Agent[];
  value: string;
  onChange: (value: string) => void;
  isLoading?: boolean;
  error?: string;
  disabled?: boolean;
}

export function AgentSelector({
  agents,
  value,
  onChange,
  isLoading,
  error,
  disabled,
}: AgentSelectorProps) {
  return (
    <div className="space-y-1">
      <label htmlFor="agent" className="label">
        Agent
      </label>
      <select
        id="agent"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || isLoading || agents.length === 0}
        className={cn(
          "input",
          error && "border-red-500 focus:border-red-500 focus:ring-red-500"
        )}
      >
        {(() => {
          if (isLoading) return <option value="">Loading agents...</option>;
          if (agents.length === 0) return <option value="">No agents found</option>;
          return (
            <>
              <option value="">Select an agent</option>
              {agents.map((agent) => (
                <option key={agent.name} value={agent.name}>
                  {agent.name}
                </option>
              ))}
            </>
          );
        })()}
      </select>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
