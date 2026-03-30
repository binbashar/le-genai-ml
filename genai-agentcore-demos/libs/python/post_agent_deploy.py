#!/usr/bin/env python3
"""
Post-deployment script to publish AgentCore Runtime ARN to SSM Parameter Store.

This script runs automatically after `agentcore launch` to update the unified
agent configuration in SSM with the deployed agent's ARN, enabling service
discovery by Streamlit and other consumers.

Usage:
    python post_agent_deploy.py <agent_name> <agent_dir>

Example:
    python post_agent_deploy.py finance_personal_assistant .

Flow:
    1. Read agent ARN from .bedrock_agentcore.yaml (written by agentcore launch)
    2. Read existing config from SSM: /agentcore/{agent_name}/config
    3. Merge ARN into config (preserving OAuth section if exists)
    4. Write updated config back to SSM

Unified Config Structure:
    {
        "arn": "arn:aws:bedrock-agentcore:...",  # Added by this script
        "oauth": {                                 # Written by Cognito CDK (optional)
            "customJWTAuthorizer": {
                "discoveryUrl": "...",
                "allowedClients": [...]
            }
        }
    }
"""

import json
import sys
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import ClientError


def get_agent_arn(agent_dir: Path) -> str:
    """
    Extract agent ARN from .bedrock_agentcore.yaml.

    Args:
        agent_dir: Path to agent directory

    Returns:
        Agent ARN string

    Raises:
        SystemExit: If file not found or ARN not present
    """
    agent_config_file = agent_dir / ".bedrock_agentcore.yaml"
    if not agent_config_file.exists():
        print(f"   ❌ Error: {agent_config_file} not found")
        print("      This script must run after `agentcore launch` completes.")
        sys.exit(1)

    with open(agent_config_file) as f:
        bedrock_config = yaml.safe_load(f)

    agents = bedrock_config.get("agents", {})
    if not agents:
        print("   ❌ Error: No agents found in .bedrock_agentcore.yaml")
        sys.exit(1)

    # Look up by default_agent, then fall back to first agent
    default_agent = bedrock_config.get("default_agent")
    if default_agent and default_agent in agents:
        agent_data = agents[default_agent]
    else:
        agent_data = next(iter(agents.values()))
    agent_arn = agent_data.get("bedrock_agentcore", {}).get("agent_arn")

    if not agent_arn:
        print("   ❌ Error: No agent ARN found in .bedrock_agentcore.yaml")
        print("      Ensure `agentcore launch` completed successfully.")
        sys.exit(1)

    return agent_arn


def update_agent_config_in_ssm(agent_name: str, agent_arn: str, region: str) -> None:
    """
    Update unified agent configuration in SSM with agent ARN.

    Reads existing config (may contain OAuth section from Cognito CDK),
    merges in agent ARN, and writes back to SSM.

    Args:
        agent_name: Agent name (e.g., "finance_personal_assistant")
        agent_arn: Agent ARN from agentcore deployment
        region: AWS region

    Raises:
        SystemExit: If SSM write fails
    """
    ssm = boto3.client("ssm", region_name=region)
    parameter_name = f"/agentcore/{agent_name}/config"

    # Read existing config from SSM (may already have OAuth section)
    existing_config = {}
    try:
        response = ssm.get_parameter(Name=parameter_name)
        existing_config = json.loads(response["Parameter"]["Value"])
        print(f"   ✅ Found existing config in SSM: {parameter_name}")
    except ssm.exceptions.ParameterNotFound:
        print("   ℹ️  No existing config in SSM, creating new parameter")
    except Exception as e:
        print(f"   ⚠️  Error reading existing config from SSM: {e}")
        print("      Proceeding with new config")

    # Merge ARN into config (preserving OAuth if exists)
    existing_config["arn"] = agent_arn

    # Write updated config to SSM
    try:
        ssm.put_parameter(
            Name=parameter_name,
            Value=json.dumps(existing_config),
            Type="String",
            Description=f"Unified configuration for {agent_name} (OAuth + ARN)",
            Overwrite=True,
        )

        auth_mode = "OAuth" if existing_config.get("oauth") else "IAM"
        print(f"   ✅ Published config to SSM: {parameter_name}")
        print(f"      Agent ARN: {agent_arn}")
        print(f"      Auth Mode: {auth_mode}")

    except ClientError as e:
        print(f"   ❌ Error writing to SSM: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python post_agent_deploy.py <agent_name> <agent_dir>")
        print("Example: python post_agent_deploy.py finance_personal_assistant .")
        sys.exit(1)

    agent_name = sys.argv[1]
    agent_dir = Path(sys.argv[2]).resolve()

    if not agent_dir.is_dir():
        print(f"Error: Agent directory not found: {agent_dir}")
        sys.exit(1)

    print("\n📝 Publishing agent configuration to SSM Parameter Store...")

    # Detect region from environment or boto3 default
    region = boto3.Session().region_name or "us-west-2"

    # Extract ARN from .bedrock_agentcore.yaml
    agent_arn = get_agent_arn(agent_dir)

    # Update unified config in SSM
    update_agent_config_in_ssm(agent_name, agent_arn, region)

    print("\n✅ Agent configuration published successfully!")
    print("   Streamlit and other services can now discover this agent via SSM.")


if __name__ == "__main__":
    main()
