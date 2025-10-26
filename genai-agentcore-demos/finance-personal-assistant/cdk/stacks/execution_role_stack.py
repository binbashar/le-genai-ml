"""IAM Execution Role Stack for AgentCore Runtime.

Creates a comprehensive IAM role with all required permissions for running
an agent in Amazon Bedrock AgentCore Runtime, including memory operations.
"""

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from constructs import Construct


class ExecutionRoleStack(Stack):
    """Stack for AgentCore Runtime execution role."""

    def __init__(self, scope: Construct, agent_name: str, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM execution role with trust policy
        role = iam.Role(
            self,
            "ExecutionRole",
            role_name=f"BedrockAgentCore-{agent_name}-execution-role",
            assumed_by=iam.ServicePrincipal(
                "bedrock-agentcore.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.account},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:*"
                    },
                },
            ),
            description=f"Execution role for {agent_name} AgentCore Runtime",
        )

        # ECR Image Access
        role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRImageAccess",
                effect=iam.Effect.ALLOW,
                actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/*"],
            )
        )

        # ECR Token Access
        role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRTokenAccess",
                effect=iam.Effect.ALLOW,
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )

        # CloudWatch Logs
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*"
                ],
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:DescribeLogGroups"],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:*"],
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ],
            )
        )

        # X-Ray Tracing
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                resources=["*"],
            )
        )

        # CloudWatch Metrics
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                },
            )
        )

        # AgentCore Runtime Invocation
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreRuntime",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:InvokeAgentRuntimeForUser",
                ],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:runtime/*"
                ],
            )
        )

        # AgentCore Memory - Create Memory
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreMemoryCreateMemory",
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:CreateMemory"],
                resources=["*"],
            )
        )

        # AgentCore Memory - Operations
        # IMPORTANT: Includes ListMemories with Resource: "*" as per AWS docs
        # (ListMemories doesn't support resource-level permissions)
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreMemory",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:GetMemoryRecord",
                    "bedrock-agentcore:ListActors",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:ListMemories",  # ← CRITICAL: Missing from auto-generated role
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:ListSessions",
                    "bedrock-agentcore:DeleteEvent",
                    "bedrock-agentcore:DeleteMemoryRecord",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                ],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:memory/*"
                ],
            )
        )

        # AgentCore Identity - API Key Access
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreIdentityGetResourceApiKey",
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:GetResourceApiKey"],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:token-vault/default",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:token-vault/default/apikeycredentialprovider/*",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default/workload-identity/{agent_name}-*",
                ],
            )
        )

        # AgentCore Identity - OAuth2 Client Secret Access
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreIdentityGetCredentialProviderClientSecret",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:bedrock-agentcore-identity!default/oauth2/*"
                ],
            )
        )

        # AgentCore Identity - OAuth2 Token Access
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreIdentityGetResourceOauth2Token",
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:GetResourceOauth2Token"],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:token-vault/default",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:token-vault/default/oauth2credentialprovider/*",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default/workload-identity/{agent_name}-*",
                ],
            )
        )

        # Bedrock Model Invocation
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockModelInvocation",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ApplyGuardrail",
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    f"arn:aws:bedrock:{self.region}:{self.account}:*",
                ],
            )
        )

        # AgentCore Code Interpreter
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreCodeInterpreter",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:CreateCodeInterpreter",
                    "bedrock-agentcore:StartCodeInterpreterSession",
                    "bedrock-agentcore:InvokeCodeInterpreter",
                    "bedrock-agentcore:StopCodeInterpreterSession",
                    "bedrock-agentcore:DeleteCodeInterpreter",
                    "bedrock-agentcore:ListCodeInterpreters",
                    "bedrock-agentcore:GetCodeInterpreter",
                    "bedrock-agentcore:GetCodeInterpreterSession",
                    "bedrock-agentcore:ListCodeInterpreterSessions",
                ],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:aws:code-interpreter/*",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:code-interpreter/*",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:code-interpreter-custom/*",
                ],
            )
        )

        # Store execution role ARN in SSM Parameter Store
        # Using AwsCustomResource for idempotent updates (Overwrite: true)
        parameter_name = f"/agentcore/{agent_name}/execution-role-arn"

        cr.AwsCustomResource(
            self,
            "ExecutionRoleArnParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": role.role_arn,
                    "Type": "String",
                    "Description": f"IAM execution role ARN for {agent_name} AgentCore Runtime",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"{agent_name}-execution-role-arn"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": role.role_arn,
                    "Type": "String",
                    "Description": f"IAM execution role ARN for {agent_name} AgentCore Runtime",
                    "Overwrite": True,
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,  # SSM PutParameter is in Lambda's built-in SDK
        )

        # CloudFormation Output
        CfnOutput(
            self,
            "ExecutionRoleArn",
            value=role.role_arn,
            description="AgentCore Runtime execution role ARN",
        )

        CfnOutput(
            self,
            "ExecutionRoleName",
            value=role.role_name,
            description="AgentCore Runtime execution role name",
        )

        # Store role for cross-stack references
        self.execution_role = role
        self.execution_role_arn = role.role_arn
