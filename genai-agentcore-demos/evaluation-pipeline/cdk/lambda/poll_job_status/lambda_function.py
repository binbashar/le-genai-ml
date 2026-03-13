"""
Poll Job Status Lambda - Step Functions Task

Polls the status of a Bedrock evaluation job and returns current state.
Used in Step Functions polling pattern with Wait states.

Input (from Step Functions):
{
  "job_arn": "arn:aws:bedrock:us-west-2:123456789012:evaluation-job/abc123",
  "job_name": "eval-finance-personal-assistant-20251125-120000",
  ...additional fields passed through
}

Output:
{
  "job_arn": "...",
  "job_name": "...",
  "status": "Completed|InProgress|Failed|Stopping|Stopped|Deleting",
  "failure_reasons": ["..."] (if failed),
  ...additional fields passed through
}
"""

import boto3
import json
import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_client = boto3.client("bedrock")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Poll Bedrock evaluation job status.

    Args:
        event: Job metadata from previous step
        context: Lambda context

    Returns:
        Updated job metadata with current status
    """
    logger.info(f"Received event: {json.dumps(event)}")

    job_arn = event["job_arn"]

    try:
        response = bedrock_client.get_evaluation_job(jobIdentifier=job_arn)

        status = response["status"]
        logger.info(f"Job {job_arn} status: {status}")

        # Build response preserving input fields
        result = {
            **event,  # Pass through all input fields
            "status": status,
            "failure_reasons": [],  # Always include (empty list if not failed)
        }

        # Add failure reasons if job failed
        if status == "Failed" and "failureReasons" in response:
            result["failure_reasons"] = response["failureReasons"]
            logger.error(f"Job failed: {response['failureReasons']}")

        # Add output location if completed
        if status == "Completed" and "outputDataConfig" in response:
            result["output_data_config"] = response["outputDataConfig"]

        return result

    except bedrock_client.exceptions.ResourceNotFoundException:
        logger.error(f"Evaluation job not found: {job_arn}")
        return {
            **event,
            "status": "NotFound",
            "failure_reasons": [f"Job not found: {job_arn}"],
        }

    except Exception as e:
        logger.error(f"Error polling job status: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to poll job status: {str(e)}")
