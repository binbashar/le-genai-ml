"""
Deploy Lambda functions for Gateway tools.
This script creates Lambda functions for weather_tool and length_tool.
"""
import boto3
import json
import os
import zipfile
import io
from pathlib import Path

# Configuration
REGION = os.getenv("AWS_REGION", "us-west-2")
LAMBDA_ROLE_NAME = "AgentCoreGatewayLambdaRole"  # Will be created if doesn't exist
LAMBDA_TIMEOUT = 30
LAMBDA_MEMORY = 128

# Lambda function configurations
LAMBDA_FUNCTIONS = {
    "weather-tool": {
        "handler": "weather_tool.lambda_handler",
        "description": "Dummy weather tool for AgentCore Gateway testing",
        "file": "weather_tool.py"
    },
    "length-tool": {
        "handler": "length_tool.lambda_handler",
        "description": "Dummy text length calculation tool for AgentCore Gateway testing",
        "file": "length_tool.py"
    }
}


def create_lambda_role(iam_client, role_name):
    """Create IAM role for Lambda functions if it doesn't exist."""
    try:
        # Try to get existing role
        iam_client.get_role(RoleName=role_name)
        print(f"✓ IAM role '{role_name}' already exists")
        return f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/{role_name}"
    except iam_client.exceptions.NoSuchEntityException:
        # Create new role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for AgentCore Gateway Lambda tools"
        )
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        print(f"✓ Created IAM role '{role_name}'")
        return role["Role"]["Arn"]


def create_lambda_package(function_file):
    """Create a zip package for Lambda function."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function file
        lambda_dir = Path(__file__).parent.parent / "lambda_functions"
        function_path = lambda_dir / function_file
        
        if not function_path.exists():
            raise FileNotFoundError(f"Lambda function file not found: {function_path}")
        
        zip_file.write(function_path, function_file)
    
    zip_buffer.seek(0)
    return zip_buffer.read()


def deploy_lambda_function(lambda_client, function_name, config, role_arn):
    """Deploy or update a Lambda function."""
    package = create_lambda_package(config["file"])
    
    try:
        # Try to get existing function
        existing = lambda_client.get_function(FunctionName=function_name)
        function_arn = existing["Configuration"]["FunctionArn"]
        
        # Update function code
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=package
        )
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Description=config["description"],
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Handler=config["handler"]
        )
        
        print(f"✓ Updated Lambda function '{function_name}'")
        return function_arn
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.13",
            Role=role_arn,
            Handler=config["handler"],
            Code={"ZipFile": package},
            Description=config["description"],
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Publish=True
        )
        
        function_arn = response["FunctionArn"]
        print(f"✓ Created Lambda function '{function_name}'")
        return function_arn


def main():
    """Main deployment function."""
    print("=" * 60)
    print("Deploying Lambda Functions for AgentCore Gateway")
    print("=" * 60)
    
    # Initialize AWS clients
    iam_client = boto3.client("iam", region_name=REGION)
    lambda_client = boto3.client("lambda", region_name=REGION)
    
    # Create IAM role
    print("\n1. Setting up IAM role...")
    role_arn = create_lambda_role(iam_client, LAMBDA_ROLE_NAME)
    
    # Deploy Lambda functions
    print("\n2. Deploying Lambda functions...")
    lambda_arns = {}
    
    for function_name, config in LAMBDA_FUNCTIONS.items():
        print(f"\n   Deploying {function_name}...")
        function_arn = deploy_lambda_function(
            lambda_client,
            function_name,
            config,
            role_arn
        )
        lambda_arns[function_name] = function_arn
        print(f"   ARN: {function_arn}")
    
    # Save Lambda ARNs to file for use by other scripts
    output_file = Path(__file__).parent.parent / "lambda_arns.json"
    with open(output_file, "w") as f:
        json.dump(lambda_arns, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✓ Lambda functions deployed successfully!")
    print(f"✓ Lambda ARNs saved to: {output_file}")
    print("=" * 60)
    
    return lambda_arns


if __name__ == "__main__":
    main()

