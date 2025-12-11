"""
Create Evaluation Job Lambda - Step Functions Task

Creates an AWS Bedrock evaluation job using the filtered dataset from the
previous step. Supports both Model Evaluation and RAG Evaluation (BYOI).

Model Evaluation: Evaluates LLM response quality
RAG Evaluation: Evaluates retrieval + generation quality (faithfulness, context relevance)

Input (from Step Functions):
{
  "dataset_s3_uri": "s3://bucket/evaluation-datasets/agent/timestamp/dataset.jsonl",
  "question_count": 95,
  "agent_name": "finance-personal-assistant",
  "metrics": ["Builtin.Correctness"],
  "evaluation_type": "MODEL" | "RAG_RETRIEVE_AND_GENERATE" | "RAG_RETRIEVE_ONLY",
  "output_s3_uri": "s3://bucket/evaluation-results/agent/timestamp/"
}

Output:
{
  "job_arn": "arn:aws:bedrock:us-west-2:123456789012:evaluation-job/abc123",
  "job_name": "eval-finance-personal-assistant-20251125-120000",
  "status": "InProgress"
}
"""

import boto3
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_client = boto3.client("bedrock")


def build_inference_config(evaluation_type: str, rag_source_identifier: str) -> Dict[str, Any]:
    """
    Build inference configuration based on evaluation type.

    Args:
        evaluation_type: MODEL | RAG_RETRIEVE_AND_GENERATE | RAG_RETRIEVE_ONLY
        rag_source_identifier: Identifier for the RAG source (agent name)

    Returns:
        inferenceConfig dict for create_evaluation_job API
    """
    if evaluation_type == "RAG_RETRIEVE_AND_GENERATE":
        return {
            "ragConfigs": [
                {
                    "precomputedRagSourceConfig": {
                        "retrieveAndGenerateSourceConfig": {
                            "ragSourceIdentifier": rag_source_identifier
                        }
                    }
                }
            ]
        }
    elif evaluation_type == "RAG_RETRIEVE_ONLY":
        return {
            "ragConfigs": [
                {
                    "precomputedRagSourceConfig": {
                        "retrieveSourceConfig": {
                            "ragSourceIdentifier": rag_source_identifier
                        }
                    }
                }
            ]
        }
    else:
        # Default: MODEL evaluation
        return {
            "models": [
                {
                    "precomputedInferenceSource": {
                        "inferenceSourceIdentifier": rag_source_identifier
                    }
                }
            ]
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for creating Bedrock evaluation jobs.

    Supports both Model Evaluation and RAG Evaluation (BYOI).

    Args:
        event: Configuration from Step Functions (includes dataset_s3_uri)
        context: Lambda context

    Returns:
        Job metadata including ARN and status
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Extract configuration from previous step
    dataset_s3_uri = event["dataset_s3_uri"]
    question_count = event["question_count"]
    agent_name = event.get("agent_name", "unknown")

    # Get evaluation type (MODEL | RAG_RETRIEVE_AND_GENERATE | RAG_RETRIEVE_ONLY)
    evaluation_type = event.get("evaluation_type", "MODEL")
    is_rag_evaluation = evaluation_type.startswith("RAG_")

    # Get metrics (default to Builtin.Correctness for MVP)
    metrics = event.get("metrics", ["Builtin.Correctness"])

    # Get output S3 location from environment or event
    output_s3_uri = event.get("output_s3_uri")
    if not output_s3_uri:
        bucket_name = os.environ.get("STAGING_BUCKET")
        if not bucket_name:
            raise ValueError("output_s3_uri not provided and STAGING_BUCKET not set")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_s3_uri = (
            f"s3://{bucket_name}/evaluation-results/{agent_name}/{timestamp}/"
        )

    # Get evaluation IAM role ARN from environment
    evaluation_role_arn = os.environ.get("EVALUATION_ROLE_ARN")
    if not evaluation_role_arn:
        raise ValueError("EVALUATION_ROLE_ARN environment variable not set")

    # Get judge model ID (default to Nova Pro for cost-effective testing)
    judge_model_id = os.environ.get("JUDGE_MODEL_ID", "us.amazon.nova-pro-v1:0")

    # Get RAG source / model identifier (default to agent name)
    rag_source_identifier = event.get("evaluation_model_identifier", agent_name)

    # Generate unique job name (lowercase, hyphens only)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    eval_type_suffix = "rag" if is_rag_evaluation else "model"
    job_name = f"eval-{agent_name}-{eval_type_suffix}-{timestamp}".lower().replace("_", "-")[:63]

    # Limit dataset for testing (configurable via environment variable)
    max_samples = min(
        question_count, int(os.environ.get("MAX_EVALUATION_SAMPLES", "100"))
    )

    logger.info(f"Creating {evaluation_type} evaluation job: {job_name}")
    logger.info(
        f"Dataset: {dataset_s3_uri} ({question_count} questions, limiting to {max_samples})"
    )
    logger.info(f"Judge model: {judge_model_id}")
    logger.info(f"Metrics: {metrics}")
    logger.info(f"Output: {output_s3_uri}")

    # Determine task type: Always use "General" for automated evaluation (model-as-judge)
    # Note: "Custom" task type is only for custom metrics with human evaluation
    task_type = "General"

    # Build inference configuration based on evaluation type
    inference_config = build_inference_config(evaluation_type, rag_source_identifier)

    try:
        # Build API parameters
        api_params = {
            "jobName": job_name,
            "jobDescription": f"Automated {evaluation_type} evaluation for {agent_name} using {', '.join(metrics)}",
            "roleArn": evaluation_role_arn,
            "clientRequestToken": str(uuid.uuid4()),  # Idempotency token
            # Evaluation configuration (automated with model-as-judge)
            "evaluationConfig": {
                "automated": {
                    "datasetMetricConfigs": [
                        {
                            "taskType": task_type,
                            "dataset": {
                                "name": f"{agent_name}-dataset",
                                "datasetLocation": {"s3Uri": dataset_s3_uri},
                            },
                            "metricNames": metrics,
                        }
                    ],
                    "evaluatorModelConfig": {
                        "bedrockEvaluatorModels": [{"modelIdentifier": judge_model_id}]
                    },
                }
            },
            # Inference configuration (varies by evaluation type)
            "inferenceConfig": inference_config,
            # Output configuration
            "outputDataConfig": {"s3Uri": output_s3_uri},
            # Tags for tracking
            "jobTags": [
                {"key": "AgentName", "value": agent_name},
                {"key": "Pipeline", "value": "evaluation-pipeline"},
                {"key": "EvaluationType", "value": evaluation_type},
                {"key": "CreatedBy", "value": "create-evaluation-job-lambda"},
            ],
        }

        # Add applicationType for RAG evaluation (required by API)
        if is_rag_evaluation:
            api_params["applicationType"] = "RagEvaluation"

        # Create evaluation job using AWS Bedrock API
        response = bedrock_client.create_evaluation_job(**api_params)

        job_arn = response["jobArn"]
        logger.info(f"Successfully created evaluation job: {job_arn}")

        # Return job metadata to Step Functions
        return {
            "job_arn": job_arn,
            "job_name": job_name,
            "status": "InProgress",
            "dataset_s3_uri": dataset_s3_uri,
            "output_s3_uri": output_s3_uri,
            "question_count": max_samples,
            "metrics": metrics,
            "judge_model_id": judge_model_id,
            "agent_name": agent_name,
            "evaluation_type": evaluation_type,
        }

    except bedrock_client.exceptions.ValidationException as e:
        logger.error(
            f"Validation error creating evaluation job: {str(e)}", exc_info=True
        )
        raise ValueError(f"Invalid evaluation job configuration: {str(e)}")

    except bedrock_client.exceptions.ServiceQuotaExceededException as e:
        logger.error(f"Service quota exceeded: {str(e)}", exc_info=True)
        raise RuntimeError(
            f"Service quota exceeded. Please check Bedrock limits: {str(e)}"
        )

    except bedrock_client.exceptions.ConflictException as e:
        logger.error(f"Job name conflict: {str(e)}", exc_info=True)
        raise RuntimeError(f"Evaluation job name already exists: {job_name}")

    except bedrock_client.exceptions.AccessDeniedException as e:
        logger.error(f"Access denied: {str(e)}", exc_info=True)
        raise RuntimeError(
            f"IAM permissions insufficient. Check evaluation role: {evaluation_role_arn}"
        )

    except Exception as e:
        logger.error(
            f"Unexpected error creating evaluation job: {str(e)}", exc_info=True
        )
        raise RuntimeError(f"Failed to create evaluation job: {str(e)}")


def validate_dataset_format(dataset_s3_uri: str) -> bool:
    """
    Validate that dataset exists and is in correct format.

    Note: For MVP, we trust the previous step's output.
    Future enhancement: Download and validate JSONL structure.

    Args:
        dataset_s3_uri: S3 URI of dataset

    Returns:
        True if valid
    """
    # MVP: Basic validation
    if not dataset_s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {dataset_s3_uri}")

    if not dataset_s3_uri.endswith(".jsonl"):
        raise ValueError(f"Dataset must be JSONL format: {dataset_s3_uri}")

    return True
