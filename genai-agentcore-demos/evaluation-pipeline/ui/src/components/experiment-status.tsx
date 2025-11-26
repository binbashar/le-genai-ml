"use client";

import { STATUS_CONFIG, POLLING_INTERVAL_MS } from "@/lib/constants";
import { formatDateTime, formatDuration, formatScore } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ExperimentStatusResponse, ExecutionStatus } from "@/types";

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
        <StatusBadge status={status.status} />
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
          {status.results.results?.metrics &&
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

            <div className="pt-2">
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
          </div>
        )}

      {/* New Experiment Button */}
      {status.status !== "RUNNING" && (
        <div className="mt-6 pt-4 border-t border-gray-200">
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

function StatusBadge({ status }: { status: ExecutionStatus }) {
  const config = STATUS_CONFIG[status];

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
