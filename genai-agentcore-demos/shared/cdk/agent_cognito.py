import json
from pathlib import Path
from typing import Optional

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_cognito as cognito
from aws_cdk import custom_resources as cr
from constructs import Construct


class AgentCognitoPool(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        pool_name: str,
        demo_users_file: Optional[Path] = None,
        removal_policy: RemovalPolicy = RemovalPolicy.RETAIN,
    ):
        super().__init__(scope, construct_id)

        self.user_pool = cognito.UserPool(
            self,
            "Pool",
            user_pool_name=pool_name,
            sign_in_case_sensitive=False,
            password_policy=cognito.PasswordPolicy(min_length=8),
            self_sign_up_enabled=False,
            removal_policy=removal_policy,
        )

        if demo_users_file and demo_users_file.exists():
            with open(demo_users_file) as f:
                users = json.load(f)
            for user in users:
                cognito.CfnUserPoolUser(
                    self,
                    f"User-{user['username']}",
                    user_pool_id=self.user_pool.user_pool_id,
                    username=user["username"],
                    user_attributes=[
                        cognito.CfnUserPoolUser.AttributeTypeProperty(
                            name="email", value=user["email"]
                        ),
                        cognito.CfnUserPoolUser.AttributeTypeProperty(
                            name="email_verified", value="true"
                        ),
                        cognito.CfnUserPoolUser.AttributeTypeProperty(
                            name="name", value=user["name"]
                        ),
                    ],
                    message_action="SUPPRESS",
                )

        stack = Stack.of(self)
        parameter_name = "/agentcore/shared/cognito-pool-id"

        cr.AwsCustomResource(
            self,
            "PoolIdParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": self.user_pool.user_pool_id,
                    "Type": "String",
                    "Description": "Shared Cognito User Pool ID for AgentCore agents",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "agentcore-shared-cognito-pool-id"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": self.user_pool.user_pool_id,
                    "Type": "String",
                    "Description": "Shared Cognito User Pool ID for AgentCore agents",
                    "Overwrite": True,
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,
        )

    @property
    def user_pool_id(self) -> str:
        return self.user_pool.user_pool_id

    @property
    def user_pool_arn(self) -> str:
        return self.user_pool.user_pool_arn
