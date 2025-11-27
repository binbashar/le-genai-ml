// Agent types
export interface Agent {
  name: string;
  arn: string;
}

export interface ExperimentSummary {
  executionArn: string;
  name: string;
  status: ExecutionStatus;
  startDate: string;
  stopDate?: string;
  isNoData?: boolean;
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

export interface EvaluationSuccessResult {
  job_arn: string;
  job_name: string;
  agent_name: string;
  results: {
    metrics: MetricResult[];
    output_files: string[];
    processed_at: string;
  };
}

export interface NoDataFoundResult {
  status: "NO_DATA_FOUND";
  message: string;
  filter_config: {
    agent_name: string;
    start_date: string;
    end_date: string;
    limit: number;
    metrics: string[];
  };
  filter_result: {
    dataset_s3_uri: string;
    question_count: number;
    sampling_stats: {
      total_records: number;
      sampled_records: number;
    };
  };
}

export type ExperimentResults = EvaluationSuccessResult | NoDataFoundResult;

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

// Detailed Results Types
export interface MetricScore {
  metric: string;
  score: number;
  reasoning: string;
}

export interface QuestionResult {
  prompt: string;
  response: string;
  scores: MetricScore[];
}

export interface DetailedEvaluationResults {
  summary: {
    job_arn: string;
    job_name: string;
    agent_name: string;
    metrics: MetricResult[];
    input_configuration?: Record<string, any>;
  };
  questions: QuestionResult[];
}
