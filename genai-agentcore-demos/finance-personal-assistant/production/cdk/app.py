#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from aws_cdk import App, CfnOutput, Environment, Stack, Tags

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from libs.cdk import AgentAppClient, AgentExecutionRole
from libs.cdk.agent_cognito import AgentCognitoPool

app = App()

agent_name = "finance_personal_assistant"
stack_prefix = "finance-personal-assistant"

env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)


class FinancePersonalAssistantStack(Stack):
    def __init__(self, scope: App, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool for this agent
        cognito_pool = AgentCognitoPool(
            self,
            "CognitoPool",
            pool_name="finance-personal-assistant",
            demo_users_file=Path(__file__).parent.parent.parent.parent
            / ".demo_users.json",
        )

        app_client = AgentAppClient(
            self,
            "AppClient",
            agent_name=agent_name,
            user_pool=cognito_pool.user_pool,
        )

        execution_role = AgentExecutionRole(
            self,
            "ExecutionRole",
            agent_name=agent_name,
            enable_gateway_permissions=False,
        )

        CfnOutput(self, "UserPoolId", value=cognito_pool.user_pool.user_pool_id)
        CfnOutput(self, "ClientId", value=app_client.user_pool_client_id)
        CfnOutput(self, "ExecutionRoleArn", value=execution_role.role_arn)
        CfnOutput(self, "ExecutionRoleName", value=execution_role.role_name)


stack = FinancePersonalAssistantStack(
    app,
    f"{stack_prefix}-stack",
    env=env,
)

Tags.of(app).add("Project", "GenAI-AgentCore-Demos")
Tags.of(app).add("Agent", "FinancePersonalAssistant")
Tags.of(app).add("ManagedBy", "CDK")

app.synth()
