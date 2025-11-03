#!/usr/bin/env python3
"""
Post-deployment script for AgentCore Gateway CDK stacks.

Generates local configuration files for backward compatibility:
- gateway_outputs.json: Gateway configuration (endpoint, ID, etc.)
- m2m_config.json: M2M client credentials from Secrets Manager

This enables local development without SSM/Secrets Manager calls.
"""

import argparse
import json
import sys
from pathlib import Path

import boto3


def get_stack_outputs(stack_name: str, region: str, profile: str = None) -> dict:
    """Get CloudFormation stack outputs."""
    session_kwargs = {"region_name": region}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    cfn = session.client("cloudformation")

    try:
        response = cfn.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0].get("Outputs", [])

        return {output["OutputKey"]: output["OutputValue"] for output in outputs}

    except cfn.exceptions.ClientError as e:
        if "does not exist" in str(e):
            return {}
        raise


def get_secret_value(secret_name: str, region: str, profile: str = None) -> dict:
    """Get secret value from AWS Secrets Manager."""
    session_kwargs = {"region_name": region}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    sm = session.client("secretsmanager")

    try:
        response = sm.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])

    except sm.exceptions.ResourceNotFoundException:
        print(f"⚠️  Secret not found: {secret_name}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Post-deployment script for Gateway CDK stacks"
    )
    parser.add_argument(
        "--gateway-name",
        default="agentcore-gateway",
        help="Gateway name (default: agentcore-gateway)",
    )
    parser.add_argument(
        "--stage", default="prod", help="Deployment stage (default: prod)"
    )
    parser.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region (default: us-west-2)",
    )
    parser.add_argument("--profile", help="AWS profile name (optional)")

    args = parser.parse_args()

    gateway_name = args.gateway_name
    stage = args.stage
    region = args.region
    profile = args.profile

    print(f"🔧 Generating local configuration files for {gateway_name}...")
    print(f"   Region: {region}")
    print(f"   Stage: {stage}")
    if profile:
        print(f"   Profile: {profile}")

    # Stack names follow the pattern from app.py
    cognito_stack_name = f"{gateway_name}-cognito-{stage}"
    lambda_stack_name = f"{gateway_name}-lambda-{stage}"
    gateway_stack_name = f"{gateway_name}-gateway-{stage}"

    # Get outputs from all stacks
    print("\n📥 Fetching CloudFormation stack outputs...")
    cognito_outputs = get_stack_outputs(cognito_stack_name, region, profile)
    lambda_outputs = get_stack_outputs(lambda_stack_name, region, profile)
    gateway_outputs = get_stack_outputs(gateway_stack_name, region, profile)

    if not cognito_outputs or not lambda_outputs or not gateway_outputs:
        print("❌ Error: One or more CDK stacks not found")
        print(
            f"   Expected stacks: {cognito_stack_name}, {lambda_stack_name}, {gateway_stack_name}"
        )
        sys.exit(1)

    # Generate gateway_outputs.json
    gateway_config = {
        "gateway_id": gateway_outputs.get("GatewayId"),
        "gateway_endpoint": gateway_outputs.get("GatewayEndpoint"),
        "gateway_service_role_arn": gateway_outputs.get("GatewayServiceRoleArn"),
        "lambda_execution_role_arn": lambda_outputs.get("LambdaExecutionRoleArn"),
        "cognito_user_pool_id": cognito_outputs.get("UserPoolId"),
        "m2m_client_id": cognito_outputs.get("M2MClientId"),
        "token_endpoint": cognito_outputs.get("TokenEndpoint"),
        "cognito_configured": True,
        "tools_deployed": lambda_outputs.get("ToolsDeployed", "").split(","),
        "deployed_via": "CDK",
        "region": region,
    }

    # Write gateway_outputs.json
    outputs_file = Path(__file__).parent.parent / "gateway_outputs.json"
    with open(outputs_file, "w") as f:
        json.dump(gateway_config, f, indent=2)

    print(f"✓ Created {outputs_file}")

    # Get M2M client secret from Secrets Manager
    print("\n🔐 Fetching M2M client secret from Secrets Manager...")
    secret_name = f"/agentcore/{gateway_name}/m2m-secret"
    m2m_secret = get_secret_value(secret_name, region, profile)

    if m2m_secret:
        # Write m2m_config.json
        m2m_config_file = Path(__file__).parent.parent / "m2m_config.json"
        with open(m2m_config_file, "w") as f:
            json.dump(m2m_secret, f, indent=2)

        print(f"✓ Created {m2m_config_file}")
        print("\n⚠️  SECURITY WARNING: m2m_config.json contains sensitive credentials!")
        print("   Keep this file secure and DO NOT commit to version control.")
    else:
        print("⚠️  M2M secret not found. Skipping m2m_config.json generation.")

    # Publish configuration to SSM Parameter Store
    print("\n📝 Publishing Gateway configuration to SSM Parameter Store...")

    session_kwargs = {"region_name": region}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    ssm = session.client("ssm")

    # Publish unified config to SSM (matches utils/gateway.py expectations)
    unified_config = {
        "gateway_endpoint": gateway_config["gateway_endpoint"],
        "gateway_id": gateway_config["gateway_id"],
        "region": region,
    }

    config_param_name = f"/agentcore/{gateway_name}/config"
    ssm.put_parameter(
        Name=config_param_name,
        Value=json.dumps(unified_config),
        Type="String",
        Overwrite=True,
        Description=f"Gateway configuration for {gateway_name}",
    )
    print(f"✓ Published config to SSM: {config_param_name}")

    # Summary
    print("\n✅ Post-deployment complete!")
    print("\nGenerated artifacts:")
    print("  Local files (dev convenience):")
    print(f"    - {outputs_file}")
    if m2m_secret:
        print(f"    - {m2m_config_file}")
    print("\n  SSM Parameters (production):")
    print(f"    - {config_param_name}")
    print(f"    - /agentcore/{gateway_name}/m2m-secret (Secrets Manager)")

    print("\nNext steps:")
    print("1. Test Gateway: cd ../scripts && uv run python test_m2m_auth.py")
    print("2. Configure agents: Gateway config auto-discovered via SSM")
    print("3. Verify SSM configuration:")
    print(f"   aws ssm get-parameter --name {config_param_name}")
    print(
        f"   aws secretsmanager get-secret-value --secret-id /agentcore/{gateway_name}/m2m-secret"
    )


if __name__ == "__main__":
    main()
