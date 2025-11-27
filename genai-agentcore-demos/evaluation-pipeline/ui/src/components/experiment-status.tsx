"use client";

import { STATUS_CONFIG, POLLING_INTERVAL_MS } from "@/lib/constants";
import { formatDateTime, formatDuration, formatScore } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ExperimentStatusResponse, ExecutionStatus, DetailedEvaluationResults } from "@/types";
import { DetailedResultsList } from "./detailed-results-list";
import { useState } from "react";
import { FEATURES } from "@/features";

interface ExperimentStatusProps {
  experimentName: string;
  status: ExperimentStatusResponse;
  isPolling: boolean;
  onNewExperiment: () => void;
  executionArn: string;
}

export function ExperimentStatus({
  experimentName,
  status,
  isPolling,
  onNewExperiment,
  executionArn,
}: ExperimentStatusProps) {
  const statusConfig = STATUS_CONFIG[status.status];
  const consoleUrl = getAwsConsoleUrl(executionArn);

  const [showDetails, setShowDetails] = useState(false);
  const [detailedResults, setDetailedResults] = useState<DetailedEvaluationResults | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const fetchDetails = async () => {
    if (detailedResults) {
      setShowDetails(!showDetails);
      return;
    }

    setLoadingDetails(true);
    setDetailsError(null);
    try {
      const response = await fetch(
        `/api/experiments/${encodeURIComponent(executionArn)}/details`
      );
      if (response.ok) {
        const data = await response.json();
        setDetailedResults(data);
        setShowDetails(true);
      } else {
        const err = await response.json();
        setDetailsError(err.error || "Failed to fetch details");
      }
    } catch (error) {
      console.error("Failed to fetch details:", error);
      setDetailsError("An unexpected error occurred");
    } finally {
      setLoadingDetails(false);
    }
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {experimentName}
          </h2>
          {status.startDate && (
            <p className="text-sm text-gray-500">
              Started: {formatDateTime(status.startDate)}
            </p>
          )}
        </div>
        <StatusBadge status={status.status} isNoData={status.status === "SUCCEEDED" && status.results && "status" in status.results && status.results.status === "NO_DATA_FOUND"} />
      </div>

      {/* Running State */}
      {status.status === "RUNNING" && (
        <div className="text-center py-8">
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
            <span className="font-medium">Experiment in progress...</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Polling for updates...
          </p>
          <p className="mt-1 text-xs text-gray-400">
            This may take ~8 minutes to complete
          </p>
        </div>
      )}

      {/* Success State */}
      {status.status === "SUCCEEDED" && status.results && (
        <div className="space-y-4">
          {/* Check for No Data Found */}
          {"status" in status.results &&
            status.results.status === "NO_DATA_FOUND" ? (
            <div className="rounded-md bg-gray-50 p-4 border border-gray-200">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-gray-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-gray-900">
                    No Data Found
                  </h3>
                  <div className="mt-2 text-sm text-gray-600">
                    <p>{status.results.message}</p>
                    <div className="mt-2 text-xs text-gray-500">
                      <p>Filter Configuration:</p>
                      <ul className="list-disc list-inside mt-1">
                        <li>
                          Agent: {status.results.filter_config.agent_name}
                        </li>
                        <li>
                          Date Range:{" "}
                          {formatDateTime(
                            status.results.filter_config.start_date
                          )}{" "}
                          -{" "}
                          {formatDateTime(
                            status.results.filter_config.end_date
                          )}
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Normal Success Results */
            <>
              <div className="flex items-center gap-2 text-green-700">
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span className="font-medium">Experiment Finished</span>
              </div>

              {/* Duration */}
              {status.startDate && status.stopDate && (
                <p className="text-sm text-gray-500">
                  Duration: {formatDuration(status.startDate, status.stopDate)}
                </p>
              )}

              {/* Results */}
              {"results" in status.results &&
                status.results.results.metrics &&
                status.results.results.metrics.length > 0 && (
                  <div className="border-t border-gray-200 pt-4">
                    <h3 className="text-sm font-medium text-gray-900 mb-3">
                      Evaluation Results
                    </h3>
                    <div className="space-y-2">
                      {status.results.results.metrics.map((metric) => (
                        <div
                          key={metric.name}
                          className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-md"
                        >
                          <span className="text-sm text-gray-700">
                            {metric.name.replace("Builtin.", "")}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">
                              {formatScore(metric.average_score)}
                            </span>
                            <span className="text-xs text-gray-500">
                              ({metric.sample_count} samples)
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Detailed Results Button */}
              {FEATURES.ENABLE_EVALUATION_DETAILS && (
                <div className="mt-4">
                  <button
                    onClick={fetchDetails}
                    disabled={loadingDetails}
                    className="w-full py-2 px-4 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors font-medium text-sm flex items-center justify-center gap-2"
                  >
                    {loadingDetails ? (
                      <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Loading Details...
                      </>
                    ) : (
                      <>
                        {showDetails ? "▲ Hide" : "▼ View"} Per-Question Details
                      </>
                    )}
                  </button>

                  {detailsError && (
                    <div className="mt-2 text-sm text-red-600 text-center">
                      {detailsError}
                    </div>
                  )}

                  {showDetails && detailedResults && (
                    <div className="mt-4 border-t pt-4">
                      <DetailedResultsList data={detailedResults} />
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Error State */}
      {(status.status === "FAILED" ||
        status.status === "TIMED_OUT" ||
        status.status === "ABORTED") && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-red-700">
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <span className="font-medium">
                Experiment {statusConfig.label}
              </span>
            </div>

            {status.error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm font-medium text-red-800">
                  {status.error.error}
                </p>
                <p className="text-sm text-red-700 mt-1">{status.error.cause}</p>
              </div>
            )}


          </div>
        )}

      {/* AWS Console Link */}
      <div className="mt-4 pt-4 border-t border-gray-200 flex justify-center">
        <a
          href={consoleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
        >
          View execution in AWS Console
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      {/* New Experiment Button */}
      {status.status !== "RUNNING" && (
        <div className="mt-4">
          <button onClick={onNewExperiment} className="btn-secondary w-full">
            Run New Experiment
          </button>
        </div>
      )}
    </div>
  );
}

function getAwsConsoleUrl(arn: string): string {
  try {
    // arn:aws:states:region:account:execution:stateMachineName:executionName
    const parts = arn.split(":");
    if (parts.length < 4) return "#";
    const region = parts[3];
    return `https://${region}.console.aws.amazon.com/states/home?region=${region}#/executions/details/${arn}`;
  } catch (e) {
    return "#";
  }
}

function StatusBadge({ status, isNoData }: { status: ExecutionStatus; isNoData?: boolean }) {
  const config = STATUS_CONFIG[status];

  if (isNoData) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        No Data Found
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        config.bgColor,
        config.color
      )}
    >
      {status === "RUNNING" && (
        <span className="mr-1.5 h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
      )}
      {config.label}
    </span>
  );
}
