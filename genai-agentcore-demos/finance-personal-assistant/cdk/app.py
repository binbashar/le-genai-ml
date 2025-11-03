#!/usr/bin/env python3

import os
import sys
from pathlib import Path

import boto3
from aws_cdk import App, CfnOutput, Environment, Stack, Tags
from aws_cdk import aws_cognito as cognito

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.cdk import AgentAppClient, AgentExecutionRole

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

        ssm = boto3.client("ssm", region_name=self.region)
        try:
            response = ssm.get_parameter(Name="/agentcore/shared/cognito-pool-id")
            pool_id = response["Parameter"]["Value"]
            user_pool = cognito.UserPool.from_user_pool_id(
                self,
                "ExistingUserPool",
                pool_id,
            )
        except ssm.exceptions.ParameterNotFound:
            raise RuntimeError("Shared Cognito User Pool not found.")

        app_client = AgentAppClient(
            self,
            "AppClient",
            agent_name=agent_name,
            user_pool=user_pool,
        )

        execution_role = AgentExecutionRole(
            self,
            "ExecutionRole",
            agent_name=agent_name,
            enable_gateway_permissions=True,
        )

        CfnOutput(self, "UserPoolId", value=pool_id)
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
