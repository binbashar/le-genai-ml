"""
Register Lambda functions as targets in AgentCore Gateway.
This script adds the weather and length tools to the Gateway.
"""

import boto3
import json
import os
from pathlib import Path

# Configuration
REGION = os.getenv("AWS_REGION", "us-west-2")


# Tool schemas matching the Lambda function signatures
TOOL_SCHEMAS = {
    "get-current-weather": {
        "name": "get-current-weather",
        "description": "Get current weather for a location. This is a dummy tool for testing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to get weather for",
                }
            },
            "required": ["location"],
        },
    },
    "calculate-length": {
        "name": "calculate-length",
        "description": "Calculate the length of a text string. This is a dummy tool for testing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text string to calculate length for",
                }
            },
            "required": ["text"],
        },
    },
}


def load_gateway_arn():
    """Load Gateway ARN from file."""
    gateway_file = Path(__file__).parent.parent / "gateway_arn.json"
    if not gateway_file.exists():
        raise FileNotFoundError(
            f"Gateway ARN file not found: {gateway_file}\n"
            "Please run create_gateway.py first."
        )

    with open(gateway_file) as f:
        data = json.load(f)
        return data["gatewayArn"]


def load_lambda_arns():
    """Load Lambda ARNs from file."""
    lambda_file = Path(__file__).parent.parent / "lambda_arns.json"
    if not lambda_file.exists():
        raise FileNotFoundError(
            f"Lambda ARNs file not found: {lambda_file}\n"
            "Please run deploy_lambda_functions.py first."
        )

    with open(lambda_file) as f:
        return json.load(f)


def register_target(client, gateway_arn, tool_name, tool_schema, lambda_arn):
    """
    Register a Lambda function as a Gateway target.

    Note: The exact API method name may vary. If you encounter errors,
    check the AWS Bedrock AgentCore API documentation for the correct method name.
    Common alternatives: create_target, create_gateway_target, add_target
    """
    try:
        # Check if target already exists
        try:
            gateway_id = gateway_arn.split("/")[-1]
            response = client.get_gateway(gatewayIdentifier=gateway_id)
            existing_targets = response.get("gateway", {}).get("targets", [])

            for target in existing_targets:
                if target.get("name") == tool_name:
                    print(f"✓ Target '{tool_name}' already registered")
                    return target.get("targetArn")
        except Exception:
            pass

        # Register new target
        print(f"Registering target '{tool_name}'...")

        response = client.create_gateway_target(
            gatewayIdentifier=gateway_arn.split("/")[-1],
            name=tool_name,
            description=tool_schema["description"],
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {"inlinePayload": [tool_schema]},
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )

        target_arn = response.get("targetArn") or response.get("target", {}).get(
            "targetArn"
        )
        if not target_arn:
            target_arn = f"{gateway_arn}/target/{tool_name}"  # Fallback

        print(f"✓ Registered target '{tool_name}'")
        print(f"  Target ARN: {target_arn}")

        return target_arn

    except Exception as e:
        print(f"✗ Error registering target '{tool_name}': {str(e)}")
        print(f"  Gateway ARN: {gateway_arn}")
        print(f"  Lambda ARN: {lambda_arn}")
        print(
            f"\n  Tip: Check AWS Bedrock AgentCore API documentation for correct method name."
        )
        raise


def main():
    """Main function to register Lambda targets."""
    print("=" * 60)
    print("Registering Lambda Targets in AgentCore Gateway")
    print("=" * 60)

    # Load Gateway and Lambda ARNs
    print("\n1. Loading configuration...")
    gateway_arn = load_gateway_arn()
    lambda_arns = load_lambda_arns()

    print(f"   Gateway ARN: {gateway_arn}")
    print(f"   Lambda functions: {list(lambda_arns.keys())}")

    # Initialize AWS client (use control client for Gateway operations)
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    # Map Lambda functions to tools
    lambda_to_tool = {
        "weather-tool": ("get-current-weather", lambda_arns["weather-tool"]),
        "length-tool": ("calculate-length", lambda_arns["length-tool"]),
    }

    # Register targets
    print("\n2. Registering targets...")
    target_arns = {}

    for lambda_name, (tool_name, lambda_arn) in lambda_to_tool.items():
        print(f"\n   Registering {tool_name} -> {lambda_name}...")
        tool_schema = TOOL_SCHEMAS[tool_name]
        target_arn = register_target(
            client, gateway_arn, tool_name, tool_schema, lambda_arn
        )
        target_arns[tool_name] = target_arn

    # Save target ARNs
    output_file = Path(__file__).parent.parent / "gateway_targets.json"
    with open(output_file, "w") as f:
        json.dump({"gatewayArn": gateway_arn, "targets": target_arns}, f, indent=2)

    print("\n" + "=" * 60)
    print("✓ All targets registered successfully!")
    print(f"✓ Target ARNs saved to: {output_file}")
    print("=" * 60)

    return target_arns


if __name__ == "__main__":
    main()
