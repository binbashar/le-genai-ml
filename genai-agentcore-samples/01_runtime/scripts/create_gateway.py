"""
Create AgentCore Gateway for tool invocation.
This script creates a Gateway that will be used to route tool calls to Lambda functions.
"""
import boto3
import json
import os
import time
from pathlib import Path

# Configuration
REGION = os.getenv("AWS_REGION", "us-west-2")
GATEWAY_NAME = "translator-agent-gateway"
GATEWAY_DESCRIPTION = "Gateway for translator agent dummy tools"
GATEWAY_ROLE_NAME = "AgentCoreGatewayRole"  # IAM role for Gateway


def create_gateway_role(iam_client, role_name, region):
    """Create IAM role for Gateway if it doesn't exist."""
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    try:
        # Try to get existing role
        iam_client.get_role(RoleName=role_name)
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        print(f"✓ IAM role '{role_name}' already exists")
        return role_arn
    except iam_client.exceptions.NoSuchEntityException:
        # Create new role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock-agentcore.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceAccount": account_id
                        },
                        "ArnLike": {
                            "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/*"
                        }
                    }
                }
            ]
        }
        
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for AgentCore Gateway"
        )
        
        # Attach basic execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        role_arn = role["Role"]["Arn"]
        print(f"✓ Created IAM role '{role_name}'")
        return role_arn


def wait_for_gateway_active(client, gateway_arn, max_retries=30, retry_delay=5):
    """Wait for Gateway to become active."""
    gateway_id = gateway_arn.split("/")[-1]
    
    for attempt in range(max_retries):
        try:
            response = client.get_gateway(gatewayIdentifier=gateway_id)
            status = response.get("gateway", {}).get("status", "UNKNOWN")
            
            if status in ["ACTIVE", "READY"]:
                print(f"✓ Gateway is now {status}")
                return True
            elif status in ["FAILED", "DELETING", "DELETED"]:
                raise Exception(f"Gateway creation failed with status: {status}")
            
            print(f"⏳ Gateway status: {status}, waiting {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                # Gateway might not be immediately available
                print(f"⏳ Gateway not yet available, waiting {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise
    
    raise Exception(f"Gateway did not become ACTIVE after {max_retries * retry_delay} seconds")


def create_gateway(client, gateway_name, description, role_arn):
    """Create or get existing AgentCore Gateway."""
    try:
        # List existing gateways to check if one with this name exists
        response = client.list_gateways()
        
        for gateway in response.get("gatewaySummaries", []):
            if gateway["name"] == gateway_name:
                gateway_arn = gateway["gatewayArn"]
                print(f"✓ Gateway '{gateway_name}' already exists")
                print(f"  ARN: {gateway_arn}")
                return gateway_arn
        
        # Create new gateway
        print(f"Creating Gateway '{gateway_name}'...")
        # According to AWS docs, for AWS_IAM authorizerType, authorizerConfiguration should be omitted
        # However, the API may require it. If omitting fails, we'll need to use CUSTOM_JWT with OAuth setup
        response = client.create_gateway(
            name=gateway_name,
            description=description,
            roleArn=role_arn,
            protocolType="MCP",  # Model Context Protocol
            authorizerType="NONE",  # Use AWS IAM for authorization
            # authorizerConfiguration={
            #     "customJWTAuthorizer": {"discoveryUrl": ""}
            # }# Note: authorizerConfiguration is omitted for AWS_IAM per AWS documentation
        )
        
        gateway_arn = response["gatewayArn"]
        print(f"✓ Created Gateway '{gateway_name}'")
        print(f"  ARN: {gateway_arn}")
        
        # Wait for Gateway to become active
        print("\nWaiting for Gateway to become active...")
        wait_for_gateway_active(client, gateway_arn)
        
        return gateway_arn
        
    except Exception as e:
        print(f"✗ Error creating gateway: {str(e)}")
        raise


def main():
    """Main function to create Gateway."""
    print("=" * 60)
    print("Creating AgentCore Gateway")
    print("=" * 60)
    
    # Initialize AWS clients
    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    iam_client = boto3.client("iam", region_name=REGION)
    
    # Create IAM role for Gateway
    print("\n1. Setting up IAM role for Gateway...")
    role_arn = create_gateway_role(iam_client, GATEWAY_ROLE_NAME, REGION)
    print(f"   Role ARN: {role_arn}")
    
    # Create Gateway
    print(f"\n2. Creating Gateway...")
    print(f"   Gateway Name: {GATEWAY_NAME}")
    print(f"   Region: {REGION}\n")
    
    gateway_arn = create_gateway(control_client, GATEWAY_NAME, GATEWAY_DESCRIPTION, role_arn)
    
    # Save Gateway ARN to file
    output_file = Path(__file__).parent.parent / "gateway_arn.json"
    with open(output_file, "w") as f:
        json.dump({
            "gatewayArn": gateway_arn,
            "gatewayName": GATEWAY_NAME,
            "region": REGION,
            "roleArn": role_arn
        }, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✓ Gateway created successfully!")
    print(f"✓ Gateway ARN saved to: {output_file}")
    print("=" * 60)
    
    return gateway_arn


if __name__ == "__main__":
    main()

