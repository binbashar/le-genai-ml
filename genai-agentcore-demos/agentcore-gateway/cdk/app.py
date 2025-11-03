#!/usr/bin/env python3
"""
AgentCore Gateway CDK Application

This CDK app creates the complete infrastructure for an independent AgentCore Gateway:
- Cognito User Pool for M2M authentication
- Lambda functions for MCP tools
- AgentCore Gateway with OAuth JWT authorizer
- SSM parameters for configuration discovery
- Secrets Manager for sensitive credentials
"""

import os

import aws_cdk as cdk
from stacks.cognito_stack import GatewayCognitoStack
from stacks.gateway_stack import GatewayStack
from stacks.lambda_stack import GatewayLambdaStack

app = cdk.App()

# Get environment configuration
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-west-2"),
)

# Gateway configuration
gateway_name = app.node.try_get_context("gateway_name") or "agentcore-gateway"
stage = app.node.try_get_context("stage") or "prod"

# Stack 1: Cognito User Pool for Gateway M2M authentication
cognito_stack = GatewayCognitoStack(
    app,
    f"{gateway_name}-cognito-{stage}",
    gateway_name=gateway_name,
    env=env,
    description=f"Cognito User Pool for {gateway_name} M2M authentication",
)

# Stack 2: Lambda functions for MCP tools
lambda_stack = GatewayLambdaStack(
    app,
    f"{gateway_name}-lambda-{stage}",
    gateway_name=gateway_name,
    env=env,
    description=f"Lambda functions for {gateway_name} MCP tools",
)

# Stack 3: AgentCore Gateway with targets
gateway_stack = GatewayStack(
    app,
    f"{gateway_name}-gateway-{stage}",
    gateway_name=gateway_name,
    cognito_stack=cognito_stack,
    lambda_stack=lambda_stack,
    env=env,
    description=f"AgentCore Gateway infrastructure for {gateway_name}",
)

# Dependency chain: Cognito -> Lambda -> Gateway
lambda_stack.add_dependency(cognito_stack)
gateway_stack.add_dependency(lambda_stack)

# Tags for all resources
cdk.Tags.of(app).add("Project", "GenAI-AgentCore-Demos")
cdk.Tags.of(app).add("Component", "AgentCore-Gateway")
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
