"use client";

import { useState } from "react";
import { ExperimentForm } from "@/components/experiment-form";
import { ExperimentStatus } from "@/components/experiment-status";
import { useStartExperiment } from "@/hooks/use-start-experiment";
import { useExperimentStatus } from "@/hooks/use-experiment-status";
import type { ExperimentFormSchema } from "@/lib/schemas";
import type { Agent } from "@/types";

import { ArrowLeftIcon } from "@heroicons/react/24/outline";

interface ActiveExperiment {
    executionArn: string;
    name: string;
}

interface ExperimentContainerProps {
    initialAgents: Agent[];
    agentsWarning?: string;
    onBack?: () => void;
}

export function ExperimentContainer({ initialAgents, agentsWarning, onBack }: ExperimentContainerProps) {
    const [activeExperiment, setActiveExperiment] =
        useState<ActiveExperiment | null>(null);

    // Mutation for starting experiments
    const startExperimentMutation = useStartExperiment();

    // Query for polling experiment status
    const {
        data: statusData,
        isLoading: isLoadingStatus,
        error: statusError,
        isFetching: isPolling,
    } = useExperimentStatus(activeExperiment?.executionArn ?? null);

    const handleSubmit = async (data: ExperimentFormSchema) => {
        try {
            const result = await startExperimentMutation.mutateAsync(data);
            setActiveExperiment({
                executionArn: result.executionArn,
                name: data.experimentName,
            });
        } catch (error) {
            // Error is handled by mutation state
            console.error("Failed to start experiment:", error);
        }
    };

    const handleNewExperiment = () => {
        setActiveExperiment(null);
        startExperimentMutation.reset();
    };

    // Show status view if experiment is active
    if (activeExperiment && statusData) {
        return (
            <div className="max-w-2xl mx-auto">
                <ExperimentStatus
                    experimentName={activeExperiment.name}
                    status={statusData}
                    isPolling={isPolling}
                    onNewExperiment={handleNewExperiment}
                    executionArn={activeExperiment.executionArn}
                />
            </div>
        );
    }

    // Show loading state while fetching initial status
    if (activeExperiment && isLoadingStatus) {
        return (
            <div className="max-w-2xl mx-auto">
                <div className="card text-center py-12">
                    <div className="inline-flex items-center gap-2 text-blue-600">
                        <svg
                            className="animate-spin h-5 w-5"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                        </svg>
                        <span className="font-medium">Starting experiment...</span>
                    </div>
                </div>
            </div>
        );
    }

    // Show error state
    if (statusError) {
        return (
            <div className="max-w-2xl mx-auto">
                <div className="card">
                    <div className="text-center py-8">
                        <p className="text-red-600 font-medium">
                            Error loading experiment status
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                            {statusError instanceof Error
                                ? statusError.message
                                : "Unknown error"}
                        </p>
                        <button
                            onClick={handleNewExperiment}
                            className="btn-secondary mt-4"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Show form
    return (
        <div className="max-w-2xl mx-auto">
            {onBack && (
                <button
                    onClick={onBack}
                    className="mb-6 inline-flex items-center gap-x-1 text-sm font-semibold text-gray-900 hover:text-gray-600"
                >
                    <ArrowLeftIcon className="h-4 w-4" />
                    Back to List
                </button>
            )}

            {agentsWarning && (
                <div className="mb-4 p-3 rounded-md bg-yellow-50 border border-yellow-200">
                    <p className="text-sm text-yellow-700">{agentsWarning}</p>
                </div>
            )}

            <ExperimentForm
                agents={initialAgents}
                isLoadingAgents={false}
                onSubmit={handleSubmit}
                isSubmitting={startExperimentMutation.isPending}
                submitError={
                    startExperimentMutation.error instanceof Error
                        ? startExperimentMutation.error.message
                        : undefined
                }
            />
        </div>
    );
}
