#!/usr/bin/env python3
"""
CDK Stack for Chat Agent Infrastructure

Creates a named IAM execution role for agent identification in the evaluation pipeline.
The role name follows the pattern: BedrockAgentCore-{agent_name}-execution-role

This enables the evaluation pipeline to identify which agent made each Bedrock
model invocation by parsing the IAM role ARN from CloudWatch logs.
"""

import os
import sys
from pathlib import Path

from aws_cdk import App, CfnOutput, Environment, Stack, Tags

# Add libs to path for AgentExecutionRole construct
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from libs.cdk import AgentExecutionRole

app = App()

agent_name = "chat_agent"
stack_prefix = "chat-agent"

env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)


class ChatAgentStack(Stack):
    """Minimal CDK stack for chat_agent with named execution role."""

    def __init__(self, scope: App, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create named execution role for agent identification
        # Role name: BedrockAgentCore-chat_agent-execution-role
        # Publishes to SSM: /agentcore/chat_agent/execution-role-arn
        execution_role = AgentExecutionRole(
            self,
            "ExecutionRole",
            agent_name=agent_name,
            enable_gateway_permissions=False,
        )

        CfnOutput(self, "ExecutionRoleArn", value=execution_role.role_arn)
        CfnOutput(self, "ExecutionRoleName", value=execution_role.role_name)


stack = ChatAgentStack(app, f"{stack_prefix}-stack", env=env)

Tags.of(app).add("Project", "GenAI-AgentCore-Demos")
Tags.of(app).add("Agent", "ChatAgent")
Tags.of(app).add("ManagedBy", "CDK")

app.synth()
