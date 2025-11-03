"""
Cognito Stack for AgentCore Gateway M2M Authentication

Creates a dedicated Cognito User Pool for Gateway with:
- M2M app client for Client Credentials OAuth flow
- Resource server with custom scope (agentcore-gateway/access)
- Cognito domain for OAuth2 token endpoint
- SSM Parameter Store for OAuth configuration
- AWS Secrets Manager for M2M client credentials
"""

import json

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import custom_resources as cr
from constructs import Construct


class GatewayCognitoStack(Stack):
    """Stack for Gateway's dedicated Cognito User Pool with M2M authentication."""

    def __init__(
        self, scope: Construct, construct_id: str, gateway_name: str, **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create User Pool for Gateway M2M authentication
        # No user sign-up, password policy, or user auth flows - M2M only
        self.pool = cognito.UserPool(
            self,
            "GatewayUserPool",
            user_pool_name=f"AgentCore-{gateway_name}",
            self_sign_up_enabled=False,
            sign_in_case_sensitive=False,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/test environments
            # Advanced security mode removed - requires Cognito Plus plan
        )

        # Create resource server for custom scopes
        # This enables "agentcore-gateway/access" scope for M2M clients
        resource_server = self.pool.add_resource_server(
            "GatewayResourceServer",
            identifier="agentcore-gateway",
            scopes=[
                cognito.ResourceServerScope(
                    scope_name="access",
                    scope_description="Access to AgentCore Gateway MCP tools",
                )
            ],
        )

        # Create M2M app client with Client Credentials flow
        # No user authentication flows - only M2M machine-to-machine
        self.m2m_client = self.pool.add_client(
            "M2MClient",
            user_pool_client_name=f"{gateway_name}-m2m-client",
            # No user auth flows for M2M
            auth_flows=cognito.AuthFlow(
                user_password=False,
                user_srp=False,
                admin_user_password=False,
                custom=False,
            ),
            # OAuth2 Client Credentials flow only
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    client_credentials=True,  # M2M OAuth2 flow
                    authorization_code_grant=False,
                    implicit_code_grant=False,
                ),
                scopes=[
                    cognito.OAuthScope.custom(
                        f"{resource_server.user_pool_resource_server_id}/access"
                    )
                ],
            ),
            # Token validity
            access_token_validity=Duration.hours(1),
            # Generate client secret for M2M authentication
            generate_secret=True,
        )

        # Create Cognito domain for OAuth2 token endpoint
        # Required for M2M Client Credentials flow (/oauth2/token)
        # Domain format: {gateway_name}.auth.{region}.amazoncognito.com
        domain_prefix = gateway_name.replace("_", "-")  # Hyphens only
        self.domain = self.pool.add_domain(
            "GatewayDomain",
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=domain_prefix),
        )

        # Store M2M client credentials in Secrets Manager
        m2m_secret_value = {
            "client_id": self.m2m_client.user_pool_client_id,
            "client_secret": self.m2m_client.user_pool_client_secret.unsafe_unwrap(),
            "token_endpoint": f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token",
            "scope": f"{resource_server.user_pool_resource_server_id}/access",
        }

        from aws_cdk import SecretValue

        self.m2m_secret = secretsmanager.Secret(
            self,
            "M2MClientSecret",
            secret_name=f"/agentcore/{gateway_name}/m2m-secret",
            description=f"M2M client credentials for {gateway_name}",
            secret_object_value={
                "client_id": SecretValue.unsafe_plain_text(
                    self.m2m_client.user_pool_client_id
                ),
                "client_secret": self.m2m_client.user_pool_client_secret,
                "token_endpoint": SecretValue.unsafe_plain_text(
                    f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token"
                ),
                "scope": SecretValue.unsafe_plain_text(
                    f"{resource_server.user_pool_resource_server_id}/access"
                ),
            },
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Store OAuth configuration in SSM Parameter Store
        oauth_config = {
            "customJWTAuthorizer": {
                "discoveryUrl": f"https://cognito-idp.{self.region}.amazonaws.com/{self.pool.user_pool_id}/.well-known/openid-configuration",
                "allowedClients": [self.m2m_client.user_pool_client_id],
            }
        }

        oauth_config_json = json.dumps(oauth_config)
        oauth_param_name = f"/agentcore/{gateway_name}/oauth-config"

        cr.AwsCustomResource(
            self,
            "OAuthConfigParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": oauth_param_name,
                    "Value": oauth_config_json,
                    "Type": "String",
                    "Description": f"OAuth2 authorizer configuration for {gateway_name} Gateway",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"{gateway_name}-oauth-config"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": oauth_param_name,
                    "Value": oauth_config_json,
                    "Type": "String",
                    "Description": f"OAuth2 authorizer configuration for {gateway_name} Gateway",
                    "Overwrite": True,
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,  # SSM is in Lambda's built-in SDK
        )

        # CloudFormation Outputs
        CfnOutput(
            self,
            "UserPoolId",
            value=self.pool.user_pool_id,
            description="Cognito User Pool ID for Gateway M2M authentication",
        )

        CfnOutput(
            self,
            "M2MClientId",
            value=self.m2m_client.user_pool_client_id,
            description="M2M App Client ID for Client Credentials flow",
        )

        CfnOutput(
            self,
            "CognitoDomain",
            value=f"{domain_prefix}.auth.{self.region}.amazoncognito.com",
            description="Cognito domain for OAuth2 token endpoint",
        )

        CfnOutput(
            self,
            "TokenEndpoint",
            value=f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token",
            description="OAuth2 token endpoint for M2M authentication",
        )

        CfnOutput(
            self,
            "M2MSecretArn",
            value=self.m2m_secret.secret_arn,
            description="Secrets Manager ARN for M2M client credentials",
        )

        CfnOutput(
            self,
            "OAuthConfigParameterName",
            value=oauth_param_name,
            description="SSM Parameter name for OAuth configuration",
        )
