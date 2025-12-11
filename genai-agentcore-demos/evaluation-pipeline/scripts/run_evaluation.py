#!/usr/bin/env python3
"""
Run evaluation pipeline from YAML configuration file.

Supports both Model Evaluation (from CloudWatch logs) and RAG Evaluation (BYOI).

Usage:
    # Model Evaluation (existing workflow)
    uv run scripts/run_evaluation.py config/runs/example.yaml
    uv run scripts/run_evaluation.py config/runs/example.yaml --wait

    # RAG Evaluation (BYOI - Bring Your Own Inference)
    uv run scripts/run_evaluation.py config/runs/rag_example.yaml --wait
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3

# Add config directory to path for config_schema_mvp import
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from config_schema_mvp import EvaluationConfig, validate_config_file

STACK_NAME = "EvaluationPipeline"


def get_staging_bucket(region: str = None) -> str:
    """Get staging bucket name from CloudFormation stack output."""
    cfn = boto3.client("cloudformation", region_name=region)

    try:
        response = cfn.describe_stacks(StackName=STACK_NAME)
        outputs = response["Stacks"][0].get("Outputs", [])

        for output in outputs:
            if output["OutputKey"] == "BucketName":
                return output["OutputValue"]

        raise ValueError(f"BucketName not found in {STACK_NAME} outputs")
    except cfn.exceptions.ClientError as e:
        if "does not exist" in str(e):
            raise ValueError(f"Stack {STACK_NAME} not found.")
        raise


def upload_dataset_to_s3(
    local_path: str, bucket_name: str, agent_name: str, region: str = None
) -> str:
    """
    Upload local JSONL dataset to S3 and return S3 URI.

    Args:
        local_path: Path to local JSONL file
        bucket_name: Target S3 bucket
        agent_name: Agent identifier for S3 key structure
        region: AWS region

    Returns:
        S3 URI of uploaded file
    """
    s3 = boto3.client("s3", region_name=region)

    # Generate timestamp-based key
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    s3_key = f"evaluation-datasets/{agent_name}/{timestamp}/dataset.jsonl"

    print(f"Uploading dataset to s3://{bucket_name}/{s3_key}")
    s3.upload_file(local_path, bucket_name, s3_key)

    return f"s3://{bucket_name}/{s3_key}"


def get_state_machine_arn(region: str = None) -> str:
    """Get Step Function ARN from CloudFormation stack output."""
    cfn = boto3.client("cloudformation", region_name=region)

    try:
        response = cfn.describe_stacks(StackName=STACK_NAME)
        outputs = response["Stacks"][0].get("Outputs", [])

        for output in outputs:
            if output["OutputKey"] == "StateMachineArn":
                return output["OutputValue"]

        raise ValueError(f"StateMachineArn not found in {STACK_NAME} outputs")
    except cfn.exceptions.ClientError as e:
        if "does not exist" in str(e):
            raise ValueError(
                f"Stack {STACK_NAME} not found. Deploy with:\n"
                "  cd cdk && uv run cdk deploy EvaluationPipelineOrchestration "
                "-c deploy_filter_lambda=true -c deploy_evaluation_job=true -c deploy_orchestration=true"
            )
        raise


def start_execution_dict(
    state_machine_arn: str, config_dict: dict, region: str = None
) -> str:
    """Start Step Function execution with config dictionary."""
    sfn = boto3.client("stepfunctions", region_name=region)

    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(config_dict),
    )

    return response["executionArn"]


def wait_for_completion(
    execution_arn: str, region: str = None, poll_interval: int = 10
) -> dict:
    """Wait for execution to complete and return final status."""
    sfn = boto3.client("stepfunctions", region_name=region)

    print(f"Waiting for execution to complete (polling every {poll_interval}s)...")

    while True:
        response = sfn.describe_execution(executionArn=execution_arn)
        status = response["status"]

        if status == "RUNNING":
            print(".", end="", flush=True)
            time.sleep(poll_interval)
        else:
            print()  # newline after dots
            return response


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation pipeline from YAML config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Model Evaluation (from CloudWatch logs)
  uv run scripts/run_evaluation.py config/runs/example.yaml
  uv run scripts/run_evaluation.py config/runs/example.yaml --wait

  # RAG Evaluation (BYOI - Bring Your Own Inference)
  uv run scripts/run_evaluation.py config/runs/rag_example.yaml --wait
        """,
    )
    parser.add_argument("config_file", help="Path to YAML configuration file")
    parser.add_argument(
        "--wait", action="store_true", help="Wait for execution to complete"
    )
    parser.add_argument(
        "--region", default="us-west-2", help="AWS region (default: us-west-2)"
    )

    args = parser.parse_args()

    # Validate config file exists
    config_path = Path(args.config_file)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    # Load and validate config
    print(f"Loading config: {config_path}")
    config, errors = validate_config_file(str(config_path))

    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Display configuration summary
    print(f"  Agent: {config.agent_name}")
    print(f"  Evaluation type: {config.evaluation_type}")

    is_rag_evaluation = config.evaluation_type.startswith("RAG_")

    if is_rag_evaluation:
        print(f"  Dataset path: {config.dataset_path}")
    else:
        print(f"  Date range: {config.start_date} to {config.end_date}")

    print(f"  Limit: {config.limit} records")
    print(f"  Metrics: {', '.join(config.metrics)}")

    # Get Step Function ARN
    try:
        state_machine_arn = get_state_machine_arn(args.region)
        print(f"\nStep Function: {state_machine_arn.split(':')[-1]}")
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # Prepare config dict for Step Functions
    config_dict = config.to_dict()

    # For RAG evaluation with local dataset, upload to S3
    if is_rag_evaluation and config.dataset_path:
        try:
            bucket_name = get_staging_bucket(args.region)
            dataset_s3_uri = upload_dataset_to_s3(
                config.dataset_path, bucket_name, config.agent_name, args.region
            )
            # Add S3 URI to config and signal to skip FilterGatherData Lambda
            config_dict["dataset_s3_uri"] = dataset_s3_uri
            config_dict["skip_filter_step"] = True
            # Remove local path from Step Functions input
            del config_dict["dataset_path"]
        except ValueError as e:
            print(f"\nError uploading dataset: {e}")
            sys.exit(1)

    # Start execution
    execution_arn = start_execution_dict(state_machine_arn, config_dict, args.region)
    print(f"\nExecution started: {execution_arn.split(':')[-1]}")

    # Optionally wait for completion
    if args.wait:
        result = wait_for_completion(execution_arn, args.region)
        status = result["status"]

        if status == "SUCCEEDED":
            print(f"Execution completed: {status}")
            if "output" in result:
                output = json.loads(result["output"])
                print(f"\nOutput:\n{json.dumps(output, indent=2)}")
        else:
            print(f"Execution {status}")
            if "error" in result:
                print(f"Error: {result.get('error')}")
                print(f"Cause: {result.get('cause')}")
            sys.exit(1)
    else:
        print("\nMonitor execution:")
        print(f"  aws stepfunctions describe-execution --execution-arn {execution_arn}")


if __name__ == "__main__":
    main()
