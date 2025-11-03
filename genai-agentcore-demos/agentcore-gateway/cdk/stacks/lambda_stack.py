"""
Lambda Stack for AgentCore Gateway Tools

Deploys Lambda functions for all MCP tools in the tools/ directory.
Each tool gets its own Lambda function with dedicated IAM execution role.

Architecture:
- One Lambda function per tool (separation of concerns)
- Shared IAM execution role (simplified management)
- Auto-discovery of tools from tools/ directory
- Supports adding new tools without code changes (convention over configuration)
"""

import json
from pathlib import Path

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class GatewayLambdaStack(Stack):
    """Stack for Gateway Lambda functions (MCP tools)."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        gateway_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Shared IAM execution role for all Lambda functions
        # Follows least privilege principle with comprehensive permissions
        self.lambda_execution_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"{gateway_name}-lambda-execution-role",
            description=f"Execution role for {gateway_name} Lambda functions",
            managed_policies=[
                # CloudWatch Logs
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
            inline_policies={
                "AdditionalPermissions": iam.PolicyDocument(
                    statements=[
                        # CloudWatch Logs (explicit)
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/{gateway_name}-*"
                            ],
                        ),
                        # X-Ray Tracing
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords",
                            ],
                            resources=["*"],
                        ),
                    ]
                )
            },
        )

        # Auto-discover tools from tools/ directory
        tools_dir = Path(__file__).parent.parent.parent / "tools"
        self.tools = {}

        # Create Lambda function for each tool
        for tool_dir in sorted(tools_dir.iterdir()):
            if not tool_dir.is_dir() or tool_dir.name.startswith("."):
                continue

            tool_name = tool_dir.name
            tool_schema_file = tool_dir / "tool_schema.json"
            tool_handler_file = tool_dir / "main.py"

            # Verify tool has required files
            if not tool_schema_file.exists():
                print(f"⚠️  Skipping {tool_name}: missing tool_schema.json")
                continue

            if not tool_handler_file.exists():
                print(f"⚠️  Skipping {tool_name}: missing main.py")
                continue

            # Read tool schema for metadata
            with open(tool_schema_file) as f:
                tool_schema = json.load(f)

            # Create Lambda function
            function = lambda_.Function(
                self,
                f"Tool-{tool_name}",
                function_name=f"{gateway_name}-{tool_name}",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="main.handler",
                code=lambda_.Code.from_asset(str(tool_dir)),
                role=self.lambda_execution_role,
                timeout=Duration.seconds(20),
                memory_size=256,
                description=tool_schema.get("description", f"{tool_name} tool"),
                environment={
                    "TOOL_NAME": tool_name,
                    "GATEWAY_NAME": gateway_name,
                },
                log_retention=logs.RetentionDays.ONE_WEEK,
                tracing=lambda_.Tracing.ACTIVE,
            )

            # Store for access by GatewayStack
            self.tools[tool_name] = {
                "function": function,
                "schema": tool_schema,
                "arn": function.function_arn,
            }

            # CloudFormation Output for each Lambda
            CfnOutput(
                self,
                f"LambdaArn-{tool_name}",
                value=function.function_arn,
                description=f"Lambda ARN for {tool_name} tool",
                export_name=f"{gateway_name}-{tool_name.replace('_', '-')}-arn",
            )

        # Summary output
        CfnOutput(
            self,
            "LambdaExecutionRoleArn",
            value=self.lambda_execution_role.role_arn,
            description="Shared Lambda execution role ARN",
        )

        CfnOutput(
            self,
            "ToolsDeployed",
            value=",".join(self.tools.keys()),
            description="List of deployed tools",
        )

    def get_tool_function(self, tool_name: str) -> lambda_.Function:
        """Get Lambda function for a tool by name."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found in deployed tools")
        return self.tools[tool_name]["function"]

    def get_tool_schema(self, tool_name: str) -> dict:
        """Get JSON schema for a tool by name."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found in deployed tools")
        return self.tools[tool_name]["schema"]

    def get_all_tools(self) -> dict:
        """Get all deployed tools with their metadata."""
        return self.tools
