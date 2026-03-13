"use client";

import { ExperimentStatus } from "@/components/experiment-status";
import { useExperimentStatus } from "@/hooks/use-experiment-status";
import { ArrowLeftIcon } from "@heroicons/react/24/outline";

interface EvaluationDetailsProps {
    executionArn: string;
    onBack: () => void;
    onNewExperiment: () => void;
}

export function EvaluationDetails({
    executionArn,
    onBack,
    onNewExperiment,
}: EvaluationDetailsProps) {
    const {
        data: statusData,
        isLoading,
        error,
        isFetching,
    } = useExperimentStatus(executionArn);

    if (isLoading) {
        return (
            <div className="max-w-2xl mx-auto space-y-6">
                <button
                    onClick={onBack}
                    className="inline-flex items-center gap-x-1 text-sm font-semibold text-gray-900 hover:text-gray-600"
                >
                    <ArrowLeftIcon className="h-4 w-4" />
                    Back to List
                </button>
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
                        <span className="font-medium">Loading details...</span>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !statusData) {
        return (
            <div className="max-w-2xl mx-auto space-y-6">
                <button
                    onClick={onBack}
                    className="inline-flex items-center gap-x-1 text-sm font-semibold text-gray-900 hover:text-gray-600"
                >
                    <ArrowLeftIcon className="h-4 w-4" />
                    Back to List
                </button>
                <div className="card">
                    <div className="text-center py-8">
                        <p className="text-red-600 font-medium">
                            Error loading evaluation details
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                            {error instanceof Error ? error.message : "Unknown error"}
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Extract experiment name from status or ARN if possible, though status usually has it if we structure it right.
    // The ExperimentStatus component expects experimentName.
    // Our status response might not have the name directly if it's just status.
    // However, the list had the name.
    // Let's assume for now we can get it or fallback.
    // Actually, ExperimentStatusResponse doesn't seem to have 'name' at the top level based on types/index.ts?
    // Let's check types.

    let experimentName = "Evaluation Details";
    if (statusData.results && "job_name" in statusData.results) {
        experimentName = statusData.results.job_name;
    }

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <button
                onClick={onBack}
                className="inline-flex items-center gap-x-1 text-sm font-semibold text-gray-900 hover:text-gray-600"
            >
                <ArrowLeftIcon className="h-4 w-4" />
                Back to List
            </button>

            <ExperimentStatus
                experimentName={experimentName}
                status={statusData}
                isPolling={isFetching}
                onNewExperiment={onNewExperiment}
                executionArn={executionArn}
            />
        </div>
    );
}
