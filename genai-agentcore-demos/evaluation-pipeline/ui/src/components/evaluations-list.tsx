
"use client";

import { useExperiments } from "@/hooks/use-experiments";
import { formatDistance, formatDistanceToNow } from "date-fns";
import { ArrowPathIcon, PlusIcon } from "@heroicons/react/24/outline";

interface EvaluationsListProps {
    onCreateClick?: () => void;
    onItemClick?: (executionArn: string) => void;
}

export function EvaluationsList({ onCreateClick, onItemClick }: EvaluationsListProps) {
    const { data: experiments, isLoading, error, refetch, isRefetching } = useExperiments();

    if (isLoading) {
        return (
            <div className="animate-pulse space-y-4">
                <div className="h-8 bg-gray-200 rounded w-1/4"></div>
                <div className="h-32 bg-gray-200 rounded"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-red-50 text-red-700 rounded-md">
                Failed to load past evaluations.
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Past Evaluations</h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => refetch()}
                        disabled={isRefetching}
                        className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100 transition-colors"
                        title="Refresh list"
                    >
                        <ArrowPathIcon className={`h-5 w-5 ${isRefetching ? "animate-spin" : ""}`} />
                    </button>
                    {onCreateClick && (
                        <button
                            onClick={onCreateClick}
                            className="inline-flex items-center gap-x-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                        >
                            <PlusIcon className="-ml-0.5 h-5 w-5" aria-hidden="true" />
                            New Evaluation
                        </button>
                    )}
                </div>
            </div>

            <div className="bg-white shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg overflow-hidden">
                <div className="min-w-full divide-y divide-gray-300">
                    <div className="bg-gray-50 px-6 py-3 grid grid-cols-12 gap-4 text-left text-sm font-semibold text-gray-900">
                        <div className="col-span-5">Name</div>
                        <div className="col-span-2">Status</div>
                        <div className="col-span-3">Started</div>
                        <div className="col-span-2">Duration</div>
                    </div>
                    <div className="divide-y divide-gray-200 bg-white">
                        {experiments?.length === 0 ? (
                            <div className="px-6 py-8 text-center text-sm text-gray-500">
                                No evaluations found.
                            </div>
                        ) : (
                            experiments?.map((experiment) => (
                                <div
                                    key={experiment.executionArn}
                                    onClick={() => onItemClick?.(experiment.executionArn)}
                                    className={`px-6 py-4 grid grid-cols-12 gap-4 text-sm items-center transition-colors ${onItemClick ? "cursor-pointer hover:bg-gray-50" : ""
                                        }`}
                                >
                                    <div className="col-span-5 font-medium text-gray-900 truncate" title={experiment.name}>
                                        {experiment.name}
                                    </div>
                                    <div className="col-span-2">
                                        <span
                                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${experiment.isNoData
                                                ? "bg-gray-100 text-gray-800"
                                                : experiment.status === "SUCCEEDED"
                                                    ? "bg-green-100 text-green-800"
                                                    : experiment.status === "RUNNING"
                                                        ? "bg-blue-100 text-blue-800"
                                                        : experiment.status === "FAILED"
                                                            ? "bg-red-100 text-red-800"
                                                            : "bg-gray-100 text-gray-800"
                                                }`}
                                        >
                                            {experiment.isNoData ? "No Data Found" : experiment.status}
                                        </span>
                                    </div>
                                    <div className="col-span-3 text-gray-500">
                                        {new Date(experiment.startDate).toLocaleDateString()} {" "}
                                        {new Date(experiment.startDate).toLocaleTimeString()}
                                    </div>
                                    <div className="col-span-2 text-gray-500">
                                        {experiment.stopDate
                                            ? formatDistance(new Date(experiment.startDate), new Date(experiment.stopDate))
                                            : "-"}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
