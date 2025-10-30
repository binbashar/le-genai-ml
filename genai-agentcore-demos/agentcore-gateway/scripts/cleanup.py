#!/usr/bin/env python3
"""
Cleanup script for AgentCore Gateway infrastructure.

Removes all resources created by deploy.py:
- Gateway and targets
- Lambda functions
- IAM roles and policies
- CloudWatch log groups

Usage:
    python cleanup.py                # Full cleanup
    python cleanup.py --dry-run      # Preview what will be deleted
    python cleanup.py --skip-iam     # Keep IAM roles
"""
import boto3
import logging
import argparse
import time
from pathlib import Path

# Import configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import *
from infrastructure.iam import delete_iam_roles
from infrastructure.lambda_deploy import delete_lambda_function
from infrastructure.gateway import delete_gateway

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def delete_cloudwatch_logs(logs_client, function_name: str):
    """Delete CloudWatch log group for Lambda function."""
    log_group = f"/aws/lambda/{function_name}"

    try:
        logs_client.delete_log_group(logGroupName=log_group)
        logger.info(f"✓ Deleted CloudWatch log group: {log_group}")
    except logs_client.exceptions.ResourceNotFoundException:
        logger.info(f"  CloudWatch log group does not exist: {log_group}")
    except Exception as e:
        logger.error(f"Failed to delete log group {log_group}: {e}")


def load_gateway_id():
    """Load gateway ID from outputs file."""
    outputs_file = Path(__file__).parent.parent / OUTPUTS_FILE

    if outputs_file.exists():
        import json
        with open(outputs_file) as f:
            outputs = json.load(f)
        return outputs.get('gateway_id')

    return None


def main():
    """Clean up all Gateway infrastructure."""

    # Parse arguments
    parser = argparse.ArgumentParser(description='Cleanup AgentCore Gateway')
    parser.add_argument('--region', default=AWS_REGION, help=f'AWS region (default: {AWS_REGION})')
    parser.add_argument('--dry-run', action='store_true', help='Preview deletions without executing')
    parser.add_argument('--skip-iam', action='store_true', help='Keep IAM roles')
    args = parser.parse_args()

    region = args.region

    print_header("AgentCore Gateway Cleanup")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No resources will be deleted")

    print(f"\nRegion: {region}")
    print(f"Gateway Name: {GATEWAY_NAME}")
    print(f"Lambda Function: {LAMBDA_FUNCTION_NAME}")

    # Confirm deletion
    if not args.dry_run:
        print("\n⚠️  This will DELETE all Gateway infrastructure!")
        confirm = input("Type 'yes' to confirm: ").strip().lower()

        if confirm != 'yes':
            print("\nCleanup cancelled")
            return

    # Initialize AWS clients
    sts = boto3.client('sts', region_name=region)
    iam = boto3.client('iam')
    lambda_client = boto3.client('lambda', region_name=region)
    logs_client = boto3.client('logs', region_name=region)
    agentcore = boto3.client('bedrock-agentcore-control', region_name=region)

    account_id = sts.get_caller_identity()['Account']
    print(f"\nAWS Account: {account_id}")

    # ========================================================================
    # Phase 1: Delete Gateway
    # ========================================================================
    print_header("Phase 1: Gateway Deletion")

    gateway_id = load_gateway_id()

    if gateway_id:
        logger.info(f"Found gateway: {gateway_id}")

        if not args.dry_run:
            delete_gateway(agentcore, gateway_id)
        else:
            logger.info(f"[DRY RUN] Would delete gateway: {gateway_id}")
    else:
        logger.info("No gateway found in outputs file")

        # Try to find by name
        try:
            gateways = agentcore.list_gateways()['gateways']
            gateway = next((g for g in gateways if g['name'] == GATEWAY_NAME), None)

            if gateway:
                logger.info(f"Found gateway by name: {gateway['gatewayId']}")

                if not args.dry_run:
                    delete_gateway(agentcore, gateway['gatewayId'])
                else:
                    logger.info(f"[DRY RUN] Would delete gateway: {gateway['gatewayId']}")
        except Exception as e:
            logger.warning(f"Could not list gateways: {e}")

    # ========================================================================
    # Phase 2: Delete Lambda Function
    # ========================================================================
    print_header("Phase 2: Lambda Function Deletion")

    if not args.dry_run:
        delete_lambda_function(lambda_client, LAMBDA_FUNCTION_NAME)
        delete_cloudwatch_logs(logs_client, LAMBDA_FUNCTION_NAME)
    else:
        logger.info(f"[DRY RUN] Would delete Lambda function: {LAMBDA_FUNCTION_NAME}")
        logger.info(f"[DRY RUN] Would delete CloudWatch logs: /aws/lambda/{LAMBDA_FUNCTION_NAME}")

    # ========================================================================
    # Phase 3: Delete IAM Roles
    # ========================================================================
    if not args.skip_iam:
        print_header("Phase 3: IAM Roles Deletion")

        if not args.dry_run:
            # Wait a bit to ensure resources are fully deleted
            logger.info("⏳ Waiting for resource cleanup...")
            time.sleep(5)

            delete_iam_roles(iam, LAMBDA_EXECUTION_ROLE_NAME, GATEWAY_SERVICE_ROLE_NAME)
        else:
            logger.info(f"[DRY RUN] Would delete IAM role: {LAMBDA_EXECUTION_ROLE_NAME}")
            logger.info(f"[DRY RUN] Would delete IAM role: {GATEWAY_SERVICE_ROLE_NAME}")
    else:
        logger.info("\nSkipping IAM role deletion (--skip-iam flag)")

    # ========================================================================
    # Phase 4: Delete Outputs File
    # ========================================================================
    outputs_file = Path(__file__).parent.parent / OUTPUTS_FILE

    if outputs_file.exists():
        if not args.dry_run:
            outputs_file.unlink()
            logger.info(f"\n✓ Deleted outputs file: {outputs_file}")
        else:
            logger.info(f"\n[DRY RUN] Would delete outputs file: {outputs_file}")

    # ========================================================================
    # Cleanup Complete
    # ========================================================================
    print_header("Cleanup Complete")

    if args.dry_run:
        print("\nDry run completed - no resources were deleted")
        print("Run without --dry-run to execute cleanup")
    else:
        print("\nAll Gateway infrastructure has been removed")
        print("\nTo redeploy: python deploy.py")

    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Cleanup failed: {e}", exc_info=True)
        sys.exit(1)
