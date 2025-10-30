#!/usr/bin/env python3
"""
Main deployment orchestration script for AgentCore Gateway.

This script follows Infrastructure as Code (IaC) best practices with modular
components that can easily be migrated to AWS CDK in the future.

Usage:
    python deploy.py                    # Full deployment
    python deploy.py --region us-east-1 # Custom region
"""

import argparse
import json
import logging
import time
from pathlib import Path

import boto3

# Import configuration
from config import (
    AWS_REGION,
    GATEWAY_DEBUG_MODE,
    GATEWAY_DESCRIPTION,
    GATEWAY_NAME,
    GATEWAY_SERVICE_ROLE_DESCRIPTION,
    GATEWAY_SERVICE_ROLE_NAME,
    GATEWAY_TARGET_DESCRIPTION,
    GATEWAY_TARGET_NAME,
    LAMBDA_ARCHITECTURE,
    LAMBDA_DESCRIPTION,
    LAMBDA_ENVIRONMENT,
    LAMBDA_EXECUTION_ROLE_DESCRIPTION,
    LAMBDA_EXECUTION_ROLE_NAME,
    LAMBDA_FUNCTION_NAME,
    LAMBDA_HANDLER,
    LAMBDA_MEMORY,
    LAMBDA_RUNTIME,
    LAMBDA_TIMEOUT,
    OUTPUTS_FILE,
    RESOURCE_TAGS,
    RESOURCE_TAGS_DICT,
)
from infrastructure.cognito import detect_cognito_config
from infrastructure.gateway import create_gateway, create_gateway_target

# Import infrastructure modules
from infrastructure.iam import create_gateway_service_role, create_lambda_execution_role
from infrastructure.lambda_deploy import deploy_lambda_function, package_lambda_code

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Simple format for user-facing script
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    """Deploy AgentCore Gateway infrastructure."""

    # Parse arguments
    parser = argparse.ArgumentParser(description="Deploy AgentCore Gateway")
    parser.add_argument(
        "--region", default=AWS_REGION, help=f"AWS region (default: {AWS_REGION})"
    )
    parser.add_argument(
        "--skip-iam", action="store_true", help="Skip IAM role creation (use existing)"
    )
    args = parser.parse_args()

    region = args.region

    print_header("AgentCore Gateway Deployment")
    print("\nDeploying MCP Gateway with calculate_budget tool")
    print(f"Region: {region}")
    print(f"Gateway Name: {GATEWAY_NAME}")
    print(f"Lambda Function: {LAMBDA_FUNCTION_NAME}")

    # Initialize AWS clients
    sts = boto3.client("sts", region_name=region)
    iam = boto3.client("iam")
    lambda_client = boto3.client("lambda", region_name=region)
    agentcore = boto3.client("bedrock-agentcore-control", region_name=region)

    # Get account ID
    account_id = sts.get_caller_identity()["Account"]
    print(f"\n📍 AWS Account: {account_id}")
    print(f"📍 AWS Region: {region}")

    # Check for existing deployment outputs
    outputs_path = Path(OUTPUTS_FILE)
    existing_outputs = None
    if outputs_path.exists():
        with open(outputs_path) as f:
            existing_outputs = json.load(f)
        logger.info("✓ Found existing deployment outputs")
        logger.info(f"  Gateway ID: {existing_outputs.get('gateway_id')}")
        logger.info(f"  Lambda ARN: {existing_outputs.get('lambda_arn')}")

    # ========================================================================
    # Phase 1: Create IAM Roles
    # ========================================================================
    print_header("Phase 1: IAM Roles")

    if args.skip_iam:
        logger.info("Skipping IAM role creation (--skip-iam flag)")
        lambda_role_arn = f"arn:aws:iam::{account_id}:role/{LAMBDA_EXECUTION_ROLE_NAME}"
        gateway_role_arn = f"arn:aws:iam::{account_id}:role/{GATEWAY_SERVICE_ROLE_NAME}"
    else:
        lambda_role_arn = create_lambda_execution_role(
            iam,
            LAMBDA_EXECUTION_ROLE_NAME,
            account_id,
            region,
            LAMBDA_EXECUTION_ROLE_DESCRIPTION,
            RESOURCE_TAGS,
        )

        gateway_role_arn = create_gateway_service_role(
            iam,
            GATEWAY_SERVICE_ROLE_NAME,
            account_id,
            region,
            GATEWAY_SERVICE_ROLE_DESCRIPTION,
            RESOURCE_TAGS,
        )

        # Wait for IAM eventual consistency
        logger.info("\n⏳ Waiting 10 seconds for IAM propagation...")
        time.sleep(10)

    # ========================================================================
    # Phase 2: Deploy Lambda Function
    # ========================================================================
    print_header("Phase 2: Lambda Function")

    # Package code
    tools_dir = Path(__file__).parent / "tools" / "calculate_budget"
    logger.info(f"Packaging Lambda code from: {tools_dir}")
    code_bytes = package_lambda_code(tools_dir)

    # Deploy function
    lambda_arn = deploy_lambda_function(
        lambda_client,
        LAMBDA_FUNCTION_NAME,
        lambda_role_arn,
        LAMBDA_HANDLER,
        LAMBDA_RUNTIME,
        LAMBDA_MEMORY,
        LAMBDA_TIMEOUT,
        LAMBDA_ARCHITECTURE,
        LAMBDA_ENVIRONMENT,
        LAMBDA_DESCRIPTION,
        code_bytes,
        RESOURCE_TAGS_DICT,
    )

    # Wait for Lambda to be ready
    logger.info("⏳ Waiting for Lambda function to be active...")
    waiter = lambda_client.get_waiter("function_active_v2")
    waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)
    logger.info("✓ Lambda function is active")

    # ========================================================================
    # Phase 3: Create Gateway
    # ========================================================================
    print_header("Phase 3: AgentCore Gateway")

    # Auto-detect Cognito configuration (for outputs file)
    agent_dir = Path(__file__).parent.parent / "finance-personal-assistant"
    cognito_config = detect_cognito_config(agent_dir)

    # Use existing gateway if available
    if existing_outputs and existing_outputs.get("gateway_id"):
        gateway_id = existing_outputs["gateway_id"]
        gateway_endpoint = existing_outputs["gateway_endpoint"]
        logger.info(f"✓ Using existing Gateway: {gateway_id}")
        logger.info(f"  Endpoint: {gateway_endpoint}")
    else:
        gateway_id, gateway_endpoint = create_gateway(
            agentcore,
            GATEWAY_NAME,
            GATEWAY_DESCRIPTION,
            gateway_role_arn,
            GATEWAY_DEBUG_MODE,
            RESOURCE_TAGS_DICT,
            cognito_config,
        )

    # ========================================================================
    # Phase 4: Add Lambda Target
    # ========================================================================
    print_header("Phase 4: Gateway Target")

    # Load tool schema
    schema_file = (
        Path(__file__).parent / "tools" / "calculate_budget" / "tool_schema.json"
    )
    with open(schema_file) as f:
        tool_schema = json.load(f)

    logger.info(f"Registering tool: {tool_schema['name']}")

    target_id = create_gateway_target(
        agentcore,
        gateway_id,
        GATEWAY_TARGET_NAME,
        GATEWAY_TARGET_DESCRIPTION,
        lambda_arn,
        tool_schema,
    )

    # ========================================================================
    # Deployment Complete - Save Outputs
    # ========================================================================
    print_header("✅ Deployment Complete")

    print(f"\n{'Gateway Details':-^70}")
    print(f"Gateway ID:       {gateway_id}")
    print(f"Gateway Endpoint: {gateway_endpoint}")
    print(f"\n{'Lambda Details':-^70}")
    print(f"Lambda ARN:       {lambda_arn}")
    print(f"\n{'Tool Details':-^70}")
    print(f"Target ID:        {target_id}")
    print(f"Tool Name:        {GATEWAY_TARGET_NAME}___{tool_schema['name']}")

    # Save outputs for agent integration
    outputs = {
        "gateway_id": gateway_id,
        "gateway_endpoint": gateway_endpoint,
        "gateway_mcp_endpoint": f"{gateway_endpoint}/mcp",
        "lambda_arn": lambda_arn,
        "target_id": target_id,
        "target_name": GATEWAY_TARGET_NAME,
        "tool_name": f"{GATEWAY_TARGET_NAME}___{tool_schema['name']}",
        "region": region,
        "account_id": account_id,
        "cognito_configured": cognito_config is not None,
    }

    outputs_file = Path(__file__).parent / OUTPUTS_FILE
    with open(outputs_file, "w") as f:
        json.dump(outputs, f, indent=2)

    print(f"\n{'Outputs':-^70}")
    print(f"Saved to: {outputs_file}")

    # ========================================================================
    # Next Steps
    # ========================================================================
    print_header("Next Steps")

    print("\n1. Test Gateway directly:")
    print(f"   cd {Path(__file__).parent}")
    print("   python scripts/test_gateway.py")

    print("\n2. Integrate with finance-personal-assistant agent:")
    print(f"   (Configuration will be auto-loaded from {OUTPUTS_FILE})")

    print("\n3. Run agent health check:")
    print("   cd ../finance-personal-assistant")
    print("   ./health.sh")

    if cognito_config:
        print("\n4. Get Cognito access token for testing:")
        print("   python scripts/get_token.py")
    else:
        print("\n⚠️  Note: No OAuth configured - Gateway will use IAM authentication")
        print(
            "   To enable OAuth, deploy Cognito stack in finance-personal-assistant/cdk"
        )

    print("\n" + "=" * 70)
    print("Deployment successful! 🎉")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"\n❌ Deployment failed: {e}", exc_info=True)
        exit(1)
