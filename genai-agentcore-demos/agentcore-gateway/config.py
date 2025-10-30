"""
Gateway configuration and constants.

This module centralizes all configuration for AgentCore Gateway deployment,
making it easy to customize for different environments or migrate to CDK.
"""

import os

# ============================================================================
# AWS Configuration
# ============================================================================

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
AWS_ACCOUNT_ID = None  # Auto-detected from STS get_caller_identity()

# ============================================================================
# Gateway Configuration
# ============================================================================

GATEWAY_NAME = "agentcore-mcp-gateway"
GATEWAY_DESCRIPTION = (
    "MCP Gateway for AgentCore demos - exposes tools as serverless functions"
)
GATEWAY_DEBUG_MODE = True  # Enable debug mode for POC (verbose logging)

# Gateway Target Configuration
GATEWAY_TARGET_NAME = "budget-tools"
GATEWAY_TARGET_DESCRIPTION = "Budget calculation and financial planning tools"

# ============================================================================
# Lambda Function Configuration
# ============================================================================

LAMBDA_FUNCTION_NAME = "agentcore-gateway-calculate-budget"
LAMBDA_DESCRIPTION = "AgentCore Gateway - Calculate Budget Tool (50/30/20 rule)"
LAMBDA_RUNTIME = "python3.13"
LAMBDA_HANDLER = "main.handler"
LAMBDA_MEMORY = 256  # MB
LAMBDA_TIMEOUT = 10  # seconds
LAMBDA_ARCHITECTURE = "x86_64"  # x86_64 or arm64

# Lambda Environment Variables (AWS_REGION is automatically set by Lambda)
LAMBDA_ENVIRONMENT = {"LOG_LEVEL": "INFO"}

# ============================================================================
# IAM Role Names
# ============================================================================

LAMBDA_EXECUTION_ROLE_NAME = "AgentCoreGatewayLambdaExecutionRole"
LAMBDA_EXECUTION_ROLE_DESCRIPTION = (
    "Execution role for AgentCore Gateway Lambda functions"
)

GATEWAY_SERVICE_ROLE_NAME = "AgentCoreGatewayServiceRole"
GATEWAY_SERVICE_ROLE_DESCRIPTION = (
    "Service role for AgentCore Gateway to invoke Lambda functions"
)

# ============================================================================
# Cognito Configuration (Optional - Auto-detected)
# ============================================================================

# Auto-detect from finance-personal-assistant deployment
COGNITO_USER_POOL_ID = None  # Populated during deployment
COGNITO_CLIENT_ID = None  # Populated during deployment
COGNITO_DISCOVERY_URL = None  # Populated during deployment

# ============================================================================
# Resource Tags
# ============================================================================

RESOURCE_TAGS = [
    {"Key": "Project", "Value": "GenAI-AgentCore-Demos"},
    {"Key": "Component", "Value": "MCP-Gateway"},
    {"Key": "Environment", "Value": "Demo"},
    {"Key": "ManagedBy", "Value": "Python-Boto3"},
]

# Dictionary format for Lambda/Gateway
RESOURCE_TAGS_DICT = {tag["Key"]: tag["Value"] for tag in RESOURCE_TAGS}

# ============================================================================
# Deployment Outputs
# ============================================================================

OUTPUTS_FILE = "gateway_outputs.json"
