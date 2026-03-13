
"use client";

import { useState } from "react";
import { EvaluationsList } from "./evaluations-list";
import { ExperimentContainer } from "./experiment-container";
import { EvaluationDetails } from "./evaluation-details";
import type { Agent } from "@/types";

interface EvaluationsDashboardProps {
    initialAgents: Agent[];
    agentsWarning?: string;
}

type View = "list" | "create" | "details";

export function EvaluationsDashboard({
    initialAgents,
    agentsWarning,
}: EvaluationsDashboardProps) {
    const [view, setView] = useState<View>("list");
    const [selectedExecutionArn, setSelectedExecutionArn] = useState<string | null>(
        null
    );

    const handleEvaluationClick = (executionArn: string) => {
        setSelectedExecutionArn(executionArn);
        setView("details");
    };

    const handleBackToList = () => {
        setView("list");
        setSelectedExecutionArn(null);
    };

    const handleNewExperiment = () => {
        setView("create");
        setSelectedExecutionArn(null);
    };

    return (
        <div className="space-y-8">
            {view === "list" && (
                <EvaluationsList
                    onCreateClick={() => setView("create")}
                    onItemClick={handleEvaluationClick}
                />
            )}

            {view === "create" && (
                <ExperimentContainer
                    initialAgents={initialAgents}
                    agentsWarning={agentsWarning}
                    onBack={handleBackToList}
                />
            )}

            {view === "details" && selectedExecutionArn && (
                <EvaluationDetails
                    executionArn={selectedExecutionArn}
                    onBack={handleBackToList}
                    onNewExperiment={handleNewExperiment}
                />
            )}
        </div>
    );
}

