#!/usr/bin/env python3
"""
Shared Cognito User Pool for AgentCore Demos

This stack creates a single Cognito User Pool shared by all agents.
This enables:
- Single sign-on across all agents
- Independent agent deployments (no deployment order dependency)
- Centralized user management

The pool ID is stored in SSM Parameter Store at:
  /agentcore/shared/cognito-pool-id

All agents reference this parameter instead of creating their own pools.
"""

import os
import sys
from pathlib import Path

from aws_cdk import App, Environment, RemovalPolicy, Stack, Tags

# Import shared construct from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent_cognito import AgentCognitoPool

app = App()

env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-west-2"),
)


class SharedCognitoStack(Stack):
    def __init__(self, scope: App, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Path to demo users file (local to this stack)
        demo_users_file = Path(__file__).parent / ".demo_users.json"

        # Create shared Cognito pool with demo users
        cognito_pool = AgentCognitoPool(
            self,
            "SharedCognitoPool",
            pool_name="AgentCore-shared",
            demo_users_file=demo_users_file if demo_users_file.exists() else None,
            removal_policy=RemovalPolicy.RETAIN,  # Don't delete users on stack deletion
        )


# Create the stack
SharedCognitoStack(
    app,
    "agentcore-shared-cognito",
    env=env,
    description="Shared Cognito User Pool for AgentCore demos (enables independent agent deployments)",
)

# Tags for all resources
Tags.of(app).add("Project", "GenAI-AgentCore-Demos")
Tags.of(app).add("Component", "Shared-Cognito")
Tags.of(app).add("ManagedBy", "CDK")

app.synth()
