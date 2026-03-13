import json

from aws_cdk import Duration, Stack
from aws_cdk import aws_cognito as cognito
from aws_cdk import custom_resources as cr
from constructs import Construct


class AgentAppClient(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_name: str,
        user_pool: cognito.IUserPool,
        access_token_validity: Duration = Duration.minutes(60),
        id_token_validity: Duration = Duration.minutes(60),
        refresh_token_validity: Duration = Duration.days(30),
    ):
        super().__init__(scope, construct_id)

        self.agent_name = agent_name
        self.user_pool = user_pool

        self.app_client = user_pool.add_client(
            "Client",
            auth_flows=cognito.AuthFlow(user_password=True),
            access_token_validity=access_token_validity,
            id_token_validity=id_token_validity,
            refresh_token_validity=refresh_token_validity,
        )

        stack = Stack.of(self)

        # Unified config structure: OAuth section only (ARN added later by post-agent-deploy)
        unified_config = {
            "oauth": {
                "customJWTAuthorizer": {
                    "discoveryUrl": f"https://cognito-idp.{stack.region}.amazonaws.com/{user_pool.user_pool_id}/.well-known/openid-configuration",
                    "allowedClients": [self.app_client.user_pool_client_id],
                }
            }
        }

        config_json = json.dumps(unified_config)
        parameter_name = f"/agentcore/{agent_name}/config"

        cr.AwsCustomResource(
            self,
            "AgentConfigParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": config_json,
                    "Type": "String",
                    "Description": f"Unified configuration for {agent_name} (OAuth + ARN)",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"{agent_name}-config"),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": config_json,
                    "Type": "String",
                    "Description": f"Unified configuration for {agent_name} (OAuth + ARN)",
                    "Overwrite": True,
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,
        )

    @property
    def user_pool_client_id(self) -> str:
        return self.app_client.user_pool_client_id
