"""Cognito Stack for OAuth2/JWT authentication.

Creates Amazon Cognito User Pool and App Client for AgentCore OAuth authentication.
Stores OAuth configuration in SSM Parameter Store for agentcore CLI integration.
"""

import json
from pathlib import Path

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_cognito as cognito
from aws_cdk import custom_resources as cr
from constructs import Construct


class CognitoStack(Stack):
    """Stack for Cognito-based OAuth2/JWT authentication."""

    def __init__(self, scope: Construct, agent_name: str, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        pool = cognito.UserPool(
            self,
            "Pool",
            user_pool_name=f"AgentCore-{agent_name}",
            sign_in_case_sensitive=False,
            password_policy=cognito.PasswordPolicy(min_length=8),
            self_sign_up_enabled=False,
        )

        client = pool.add_client(
            "Client",
            auth_flows=cognito.AuthFlow(user_password=True),
            access_token_validity=Duration.minutes(60),
            id_token_validity=Duration.minutes(60),
            refresh_token_validity=Duration.days(30),
        )

        users_file = Path(__file__).parent.parent.parent.parent / ".demo_users.json"
        if users_file.exists():
            with open(users_file) as f:
                users = json.load(f)
            for user in users:
                cognito.CfnUserPoolUser(
                    self,
                    f"User-{user['username']}",
                    user_pool_id=pool.user_pool_id,
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

        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "ClientId", value=client.user_pool_client_id)
        CfnOutput(self, "Region", value=self.region)

        # Store OAuth configuration in SSM Parameter Store
        # Using AwsCustomResource for idempotent updates (Overwrite: true)
        oauth_config = {
            "customJWTAuthorizer": {
                "discoveryUrl": f"https://cognito-idp.{self.region}.amazonaws.com/{pool.user_pool_id}/.well-known/openid-configuration",
                "allowedClients": [client.user_pool_client_id],
            }
        }

        oauth_config_json = json.dumps(oauth_config)
        parameter_name = f"/agentcore/{agent_name}/oauth-config"

        cr.AwsCustomResource(
            self,
            "OAuthConfigParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": oauth_config_json,
                    "Type": "String",
                    "Description": f"OAuth2 authorizer configuration for {agent_name} AgentCore Runtime",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"{agent_name}-oauth-config"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": oauth_config_json,
                    "Type": "String",
                    "Description": f"OAuth2 authorizer configuration for {agent_name} AgentCore Runtime",
                    "Overwrite": True,
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,  # SSM PutParameter is in Lambda's built-in SDK
        )
