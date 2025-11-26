// Agent types
export interface Agent {
  name: string;
  arn: string;
}

// Form types
export interface ExperimentFormValues {
  agentName: string;
  experimentName: string;
  startDate: Date;
  endDate: Date;
  maxLimit: number;
  metrics: string[];
}

// API request/response types
export interface StartExperimentRequest {
  agent_name: string;
  start_date: string;
  end_date: string;
  limit: number;
  metrics: string[];
}

export interface StartExperimentResponse {
  executionArn: string;
  startDate: string;
}

export interface MetricResult {
  name: string;
  average_score: number;
  sample_count: number;
}

export interface ExperimentResults {
  job_arn: string;
  job_name: string;
  agent_name: string;
  results: {
    metrics: MetricResult[];
    output_files: string[];
    processed_at: string;
  };
}

export interface ExperimentStatusResponse {
  status: ExecutionStatus;
  startDate: string;
  stopDate?: string;
  results?: ExperimentResults;
  error?: {
    cause: string;
    error: string;
  };
}

// Step Functions execution status
export type ExecutionStatus =
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "TIMED_OUT"
  | "ABORTED";

// Terminal states for polling
export const TERMINAL_STATES: ExecutionStatus[] = [
  "SUCCEEDED",
  "FAILED",
  "TIMED_OUT",
  "ABORTED",
];

export function isTerminalState(status: ExecutionStatus): boolean {
  return TERMINAL_STATES.includes(status);
}
