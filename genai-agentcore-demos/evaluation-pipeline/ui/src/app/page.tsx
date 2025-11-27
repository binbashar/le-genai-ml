import { EvaluationsDashboard } from "@/components/evaluations-dashboard";
import { discoverAgents } from "@/lib/ssm";
import type { Agent } from "@/types";

export const dynamic = 'force-dynamic';

export default async function Home() {
  let agents: Agent[] = [];
  let warning = undefined;

  try {
    agents = await discoverAgents();
    if (agents.length === 0) {
      warning = "No agents found in SSM. Deploy an agent first using 'agentcore launch'.";
    }
  } catch (error) {
    console.error("Failed to fetch agents:", error);
    warning = "Failed to fetch agents from SSM. Check server logs.";
  }

  return (
    <div className="max-w-4xl mx-auto">
      <EvaluationsDashboard
        initialAgents={agents}
        agentsWarning={warning}
      />
    </div>
  );
}
