from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from constructs import Construct


class AgentExecutionRole(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_name: str,
        enable_gateway_permissions: bool = False,
    ):
        super().__init__(scope, construct_id)

        stack = Stack.of(self)

        self.role = iam.Role(
            self,
            "ExecutionRole",
            role_name=f"BedrockAgentCore-{agent_name}-execution-role",
            assumed_by=iam.ServicePrincipal(
                "bedrock-agentcore.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": stack.account},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:*"
                    },
                },
            ),
            description=f"Execution role for {agent_name} AgentCore Runtime",
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRImageAccess",
                effect=iam.Effect.ALLOW,
                actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                resources=[f"arn:aws:ecr:{stack.region}:{stack.account}:repository/*"],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRTokenAccess",
                effect=iam.Effect.ALLOW,
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                resources=[
                    f"arn:aws:logs:{stack.region}:{stack.account}:log-group:/aws/bedrock-agentcore/runtimes/*"
                ],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:DescribeLogGroups"],
                resources=[f"arn:aws:logs:{stack.region}:{stack.account}:log-group:*"],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[
                    f"arn:aws:logs:{stack.region}:{stack.account}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ],
            )
        )

        self.role.add_to_policy(
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

        self.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                },
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreRuntime",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:InvokeAgentRuntimeForUser",
                ],
                resources=[
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:runtime/*"
                ],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreMemoryCreateMemory",
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:CreateMemory"],
                resources=["*"],
            )
        )

        self.role.add_to_policy(
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
                    "bedrock-agentcore:ListMemories",
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:ListSessions",
                    "bedrock-agentcore:DeleteEvent",
                    "bedrock-agentcore:DeleteMemoryRecord",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                ],
                resources=[
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:memory/*"
                ],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreIdentityGetResourceApiKey",
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:GetResourceApiKey"],
                resources=[
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:token-vault/default",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:token-vault/default/apikeycredentialprovider/*",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:workload-identity-directory/default/workload-identity/{agent_name}-*",
                ],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreIdentityGetCredentialProviderClientSecret",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{stack.region}:{stack.account}:secret:bedrock-agentcore-identity!default/oauth2/*"
                ],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentCoreIdentityGetResourceOauth2Token",
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:GetResourceOauth2Token"],
                resources=[
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:token-vault/default",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:token-vault/default/oauth2credentialprovider/*",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:workload-identity-directory/default",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:workload-identity-directory/default/workload-identity/{agent_name}-*",
                ],
            )
        )

        self.role.add_to_policy(
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
                    f"arn:aws:bedrock:{stack.region}:{stack.account}:*",
                ],
            )
        )

        self.role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockGuardrails",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListGuardrails",
                    "bedrock:GetGuardrail",
                ],
                resources=["*"],
            )
        )

        self.role.add_to_policy(
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
                    f"arn:aws:bedrock-agentcore:{stack.region}:aws:code-interpreter/*",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:code-interpreter/*",
                    f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:code-interpreter-custom/*",
                ],
            )
        )

        if enable_gateway_permissions:
            self.role.add_to_policy(
                iam.PolicyStatement(
                    sid="AgentCoreGatewaySSMParameterAccess",
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:GetParameter", "ssm:GetParameters"],
                    resources=[
                        f"arn:aws:ssm:{stack.region}:{stack.account}:parameter/agentcore/*/config",
                        f"arn:aws:ssm:{stack.region}:{stack.account}:parameter/agentcore/*/oauth-config",
                    ],
                )
            )

            self.role.add_to_policy(
                iam.PolicyStatement(
                    sid="AgentCoreGatewaySecretsManagerAccess",
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[
                        f"arn:aws:secretsmanager:{stack.region}:{stack.account}:secret:/agentcore/*/m2m-secret-*"
                    ],
                )
            )

            self.role.add_to_policy(
                iam.PolicyStatement(
                    sid="AgentCoreGatewayInvoke",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock-agentcore:InvokeGateway",
                        "bedrock-agentcore:GetGateway",
                    ],
                    resources=[
                        f"arn:aws:bedrock-agentcore:{stack.region}:{stack.account}:gateway/*"
                    ],
                )
            )

        parameter_name = f"/agentcore/{agent_name}/execution-role-arn"

        cr.AwsCustomResource(
            self,
            "ExecutionRoleArnParameter",
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Value": self.role.role_arn,
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
                    "Value": self.role.role_arn,
                    "Type": "String",
                    "Description": f"IAM execution role ARN for {agent_name} AgentCore Runtime",
                    "Overwrite": True,
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=False,
        )

    @property
    def role_arn(self) -> str:
        return self.role.role_arn

    @property
    def role_name(self) -> str:
        return self.role.role_name
