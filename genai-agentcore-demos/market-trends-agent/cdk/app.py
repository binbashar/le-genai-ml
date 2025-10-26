#!/usr/bin/env python3
"""CDK application for agent infrastructure.

Deploys:
1. CognitoStack: User authentication (OAuth2/JWT)
2. ExecutionRoleStack: IAM role for AgentCore Runtime

Both stacks store configuration in SSM Parameter Store.
"""

import os

from aws_cdk import App, Environment
from stacks import CognitoStack, ExecutionRoleStack

app = App()

# Agent configuration
agent_name = "market_trends_agent"
stack_prefix = "market-trends-agent"

# AWS environment (get from CDK context or environment variables)
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

# Create stacks
cognito_stack = CognitoStack(
    app,
    agent_name=agent_name,
    construct_id=f"{stack_prefix}-cognito-stack",
    env=env,
)

execution_role_stack = ExecutionRoleStack(
    app,
    agent_name=agent_name,
    construct_id=f"{stack_prefix}-execution-role-stack",
    env=env,
)

# Synthesize CloudFormation templates
app.synth()
