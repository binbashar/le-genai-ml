"""
Add Gateway permissions to AgentCore execution role.
This script adds the necessary IAM permissions for Gateway tool invocation.
"""
import boto3
import json
import os
from pathlib import Path

# Configuration
REGION = os.getenv("AWS_REGION", "us-west-2")


def load_execution_role_arn():
    """Load execution role ARN from .bedrock_agentcore.yaml."""
    config_file = Path(__file__).parent.parent / ".bedrock_agentcore.yaml"
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_file}\n"
            "Please run 'agentcore configure' first."
        )
    
    import yaml
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    # Get the default agent or first agent's execution role
    default_agent = config.get("default_agent", "")
    agents = config.get("agents", {})
    
    if default_agent and default_agent in agents:
        role_arn = agents[default_agent]["aws"]["execution_role"]
    elif agents:
        # Use first agent's role
        first_agent = list(agents.keys())[0]
        role_arn = agents[first_agent]["aws"]["execution_role"]
    else:
        raise ValueError("No agent configuration found in .bedrock_agentcore.yaml")
    
    return role_arn


def add_gateway_permissions(iam_client, role_name):
    """Add Gateway permissions to IAM role."""
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    # Gateway permissions policy
    gateway_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AgentCoreGatewayInvoke",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeGateway",
                    "bedrock-agentcore:GetGateway"
                ],
                "Resource": f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:gateway/*"
            },
            {
                "Sid": "AgentCoreGatewaySSMParameterAccess",
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameter",
                    "ssm:GetParameters"
                ],
                "Resource": [
                    f"arn:aws:ssm:{REGION}:{account_id}:parameter/agentcore/*/config",
                    f"arn:aws:ssm:{REGION}:{account_id}:parameter/agentcore/*/oauth-config"
                ]
            },
            {
                "Sid": "AgentCoreGatewaySecretsManagerAccess",
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": f"arn:aws:secretsmanager:{REGION}:{account_id}:secret:/agentcore/*/m2m-secret-*"
            },
            {
                "Sid": "LambdaInvokeForGatewayTargets",
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": f"arn:aws:lambda:{REGION}:{account_id}:function:*"
            }
        ]
    }
    
    # Create or update inline policy
    policy_name = "AgentCoreGatewayPermissions"
    
    try:
        # Try to get existing policy
        iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
        # Update existing policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(gateway_policy)
        )
        print(f"✓ Updated policy '{policy_name}' on role '{role_name}'")
    except iam_client.exceptions.NoSuchEntityException:
        # Create new policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(gateway_policy)
        )
        print(f"✓ Created policy '{policy_name}' on role '{role_name}'")


def main():
    """Main function to add Gateway permissions."""
    print("=" * 60)
    print("Adding Gateway Permissions to Execution Role")
    print("=" * 60)
    
    # Load execution role ARN
    print("\n1. Loading execution role ARN...")
    role_arn = load_execution_role_arn()
    role_name = role_arn.split("/")[-1]
    
    print(f"   Role ARN: {role_arn}")
    print(f"   Role Name: {role_name}")
    
    # Initialize IAM client
    iam_client = boto3.client("iam", region_name=REGION)
    
    # Add Gateway permissions
    print("\n2. Adding Gateway permissions...")
    add_gateway_permissions(iam_client, role_name)
    
    print("\n" + "=" * 60)
    print("✓ Gateway permissions added successfully!")
    print("=" * 60)
    print("\nThe execution role now has permissions to:")
    print("  - Invoke Gateway tools (bedrock-agentcore:InvokeGateway)")
    print("  - Get Gateway information (bedrock-agentcore:GetGateway)")
    print("  - Access SSM parameters for Gateway config")
    print("  - Access Secrets Manager for OAuth (if needed)")
    print("  - Invoke Lambda functions (for Gateway targets)")


if __name__ == "__main__":
    main()

