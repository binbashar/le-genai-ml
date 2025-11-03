"""
Gateway Stack for AgentCore Gateway

Creates AgentCore Gateway using AwsCustomResource (no native CDK support yet).
Registers Lambda tools as Gateway targets and stores configuration in SSM.

Architecture:
- Gateway with OAuth JWT authorizer (from CognitoStack)
- Gateway service IAM role for Lambda invocation
- Gateway targets for each Lambda tool (from LambdaStack)
- SSM parameters for configuration discovery

Note: Uses AwsCustomResource because AWS::BedrockAgentCore::Gateway doesn't exist in CloudFormation yet.
"""

import json

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from constructs import Construct


class GatewayStack(Stack):
    """Stack for AgentCore Gateway infrastructure."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        gateway_name: str,
        cognito_stack,
        lambda_stack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Gateway service IAM role
        # This role allows Gateway to invoke Lambda functions
        self.gateway_service_role = iam.Role(
            self,
            "GatewayServiceRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            role_name=f"{gateway_name}-service-role",
            description=f"Service role for {gateway_name} to invoke Lambda tools",
            inline_policies={
                "GatewayServicePolicy": iam.PolicyDocument(
                    statements=[
                        # Allow Gateway to invoke all tool Lambda functions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["lambda:InvokeFunction"],
                            resources=[
                                tool_info["arn"]
                                for tool_info in lambda_stack.tools.values()
                            ],
                        ),
                        # Allow Gateway to access S3 for gateway artifacts
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket",
                            ],
                            resources=[
                                f"arn:aws:s3:::bedrock-agentcore-gateway-*",
                                f"arn:aws:s3:::bedrock-agentcore-gateway-*/*",
                            ],
                        ),
                        # Allow Gateway to write logs
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/gateways/*",
                            ],
                        ),
                    ]
                )
            },
        )

        # Grant Lambda functions permission to be invoked by Gateway
        for tool_info in lambda_stack.tools.values():
            tool_info["function"].grant_invoke(self.gateway_service_role)

        # Create Gateway using AwsCustomResource
        # No native CDK support yet for AWS::BedrockAgentCore::Gateway
        gateway_config = {
            "name": gateway_name,
            "description": f"MCP Gateway for {gateway_name} tools",
            "roleArn": self.gateway_service_role.role_arn,
            "protocolType": "MCP",
            "authorizerType": "CUSTOM_JWT",
            "authorizerConfiguration": {
                "customJWTAuthorizer": {
                    "discoveryUrl": f"https://cognito-idp.{self.region}.amazonaws.com/{cognito_stack.pool.user_pool_id}/.well-known/openid-configuration",
                    "allowedClients": [cognito_stack.m2m_client.user_pool_client_id],
                }
            },
            "tags": {
                "Project": "GenAI-AgentCore-Demos",
                "Component": "AgentCore-Gateway",
                "ManagedBy": "CDK",
            },
        }

        # Custom resource for Gateway creation
        self.gateway_resource = cr.AwsCustomResource(
            self,
            "GatewayResource",
            on_create=cr.AwsSdkCall(
                service="bedrock-agentcore-control",
                action="createGateway",
                parameters=gateway_config,
                physical_resource_id=cr.PhysicalResourceId.from_response("gatewayId"),
            ),
            on_delete=cr.AwsSdkCall(
                service="bedrock-agentcore-control",
                action="deleteGateway",
                parameters={
                    "gatewayIdentifier": cr.PhysicalResourceIdReference(),
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "bedrock-agentcore:CreateGateway",
                            "bedrock-agentcore:DeleteGateway",
                            "bedrock-agentcore:GetGateway",
                            "bedrock-agentcore:ListGateways",
                            "bedrock-agentcore:TagResource",
                        ],
                        resources=["*"],
                    ),
                    # IAM PassRole for Gateway service role
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["iam:PassRole"],
                        resources=[self.gateway_service_role.role_arn],
                        conditions={
                            "StringEquals": {
                                "iam:PassedToService": "bedrock-agentcore.amazonaws.com"
                            }
                        },
                    ),
                ]
            ),
            timeout=Duration.minutes(5),
            install_latest_aws_sdk=True,  # AgentCore is new, use latest SDK
        )

        # Get Gateway ID and endpoint from custom resource
        self.gateway_id = self.gateway_resource.get_response_field("gatewayId")
        self.gateway_endpoint = self.gateway_resource.get_response_field("gatewayUrl")

        # Create Gateway targets for each Lambda tool
        self.targets = {}
        for tool_name, tool_info in lambda_stack.tools.items():
            # Create target configuration
            target_config = {
                "gatewayIdentifier": self.gateway_id,
                "name": f"{gateway_name.replace('_', '-')}-{tool_name.replace('_', '-')}",
                "description": tool_info["schema"].get(
                    "description", f"{tool_name} tool"
                ),
                "targetConfiguration": {
                    "mcp": {
                        "lambda": {
                            "lambdaArn": tool_info["arn"],
                            "toolSchema": {"inlinePayload": [tool_info["schema"]]},
                        }
                    }
                },
                "credentialProviderConfigurations": [
                    {"credentialProviderType": "GATEWAY_IAM_ROLE"}
                ],
            }

            # Custom resource for each target
            target_resource = cr.AwsCustomResource(
                self,
                f"Target-{tool_name}",
                on_create=cr.AwsSdkCall(
                    service="bedrock-agentcore-control",
                    action="createGatewayTarget",
                    parameters=target_config,
                    physical_resource_id=cr.PhysicalResourceId.from_response(
                        "targetId"
                    ),
                ),
                on_delete=cr.AwsSdkCall(
                    service="bedrock-agentcore-control",
                    action="deleteGatewayTarget",
                    parameters={
                        "gatewayIdentifier": self.gateway_id,
                        "targetIdentifier": cr.PhysicalResourceIdReference(),
                    },
                ),
                policy=cr.AwsCustomResourcePolicy.from_statements(
                    [
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock-agentcore:CreateGatewayTarget",
                                "bedrock-agentcore:DeleteGatewayTarget",
                                "bedrock-agentcore:GetGatewayTarget",
                                "bedrock-agentcore:ListGatewayTargets",
                            ],
                            resources=["*"],
                        )
                    ]
                ),
                timeout=Duration.minutes(2),
                install_latest_aws_sdk=True,
            )

            # Target must be created after Gateway
            target_resource.node.add_dependency(self.gateway_resource)

            # Store target info
            self.targets[tool_name] = {
                "resource": target_resource,
                "target_id": target_resource.get_response_field("targetId"),
                "exposed_name": f"{gateway_name}-{tool_name}___{tool_name}",
            }

        # Store Gateway configuration in SSM for discovery
        gateway_config_json = json.dumps(
            {
                "gateway_id": self.gateway_id,
                "gateway_endpoint": self.gateway_endpoint,
                "m2m_client_id": cognito_stack.m2m_client.user_pool_client_id,
                "token_endpoint": f"https://{gateway_name.replace('_', '-')}.auth.{self.region}.amazoncognito.com/oauth2/token",
                "cognito_configured": True,
                "tools": list(self.targets.keys()),
            }
        )

        config_param_name = f"/agentcore/{gateway_name}/config"

        self.config_parameter = cr.AwsCustomResource(
            self,
            "ConfigParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": config_param_name,
                    "Value": gateway_config_json,
                    "Type": "String",
                    "Description": f"Gateway configuration for {gateway_name}",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"{gateway_name}-config"),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": config_param_name,
                    "Value": gateway_config_json,
                    "Type": "String",
                    "Description": f"Gateway configuration for {gateway_name}",
                    "Overwrite": True,
                },
            ),
            on_delete=cr.AwsSdkCall(
                service="SSM",
                action="deleteParameter",
                parameters={"Name": config_param_name},
                # Ignore errors if parameter doesn't exist
                ignore_error_codes_matching="ParameterNotFound",
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,  # SSM is in built-in SDK
        )

        # Config must be created after all targets
        for target_info in self.targets.values():
            self.config_parameter.node.add_dependency(target_info["resource"])

        # CloudFormation Outputs
        CfnOutput(
            self,
            "GatewayId",
            value=self.gateway_id,
            description="AgentCore Gateway ID",
        )

        CfnOutput(
            self,
            "GatewayEndpoint",
            value=self.gateway_endpoint,
            description="AgentCore Gateway MCP endpoint",
        )

        CfnOutput(
            self,
            "GatewayServiceRoleArn",
            value=self.gateway_service_role.role_arn,
            description="Gateway service role ARN",
        )

        CfnOutput(
            self,
            "ConfigParameterName",
            value=config_param_name,
            description="SSM Parameter name for Gateway configuration",
        )

        CfnOutput(
            self,
            "TargetsCount",
            value=str(len(self.targets)),
            description="Number of deployed Gateway targets",
        )
