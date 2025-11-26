#!/usr/bin/env python3
"""
Run evaluation pipeline from YAML configuration file.

Usage:
    uv run scripts/run_evaluation.py config/runs/example.yaml
    uv run scripts/run_evaluation.py config/runs/example.yaml --wait
"""

import argparse
import json
import sys
import time
from pathlib import Path

import boto3

# Add config directory to path for config_schema_mvp import
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from config_schema_mvp import EvaluationConfig, validate_config_file

STACK_NAME = "EvaluationPipelineOrchestration"


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


def start_execution(state_machine_arn: str, config: EvaluationConfig, region: str = None) -> str:
    """Start Step Function execution with config."""
    sfn = boto3.client("stepfunctions", region_name=region)

    response = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(config.to_dict()),
    )

    return response["executionArn"]


def wait_for_completion(execution_arn: str, region: str = None, poll_interval: int = 10) -> dict:
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
  uv run scripts/run_evaluation.py config/runs/example.yaml
  uv run scripts/run_evaluation.py config/runs/example.yaml --wait
  uv run scripts/run_evaluation.py config/runs/example.yaml --region us-west-2
        """,
    )
    parser.add_argument("config_file", help="Path to YAML configuration file")
    parser.add_argument("--wait", action="store_true", help="Wait for execution to complete")
    parser.add_argument("--region", default="us-west-2", help="AWS region (default: us-west-2)")

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

    print(f"  Agent: {config.agent_name}")
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

    # Start execution
    execution_arn = start_execution(state_machine_arn, config, args.region)
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
