"""
MVP Orchestration Stack - Configuration Echo Test

Goal: Test that Step Functions can read YAML config and invoke Lambda
This is the absolute minimum to validate connectivity before building full pipeline.

Components:
- Lambda function: Echoes configuration back
- Step Functions: Single state that invokes Lambda
- Test: Pass config from YAML → Step Functions → Lambda → Response
"""

import json
from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_stepfunctions as sfn,
)
from constructs import Construct


class MvpOrchestrationStack(Stack):
    """
    MVP stack for testing Step Functions configuration passing

    This is phase 1 of the orchestration pipeline: prove we can read config
    and pass it through AWS infrastructure before building complex logic.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = self.region

        # =====================================================================
        # Lambda Function: Echo Configuration
        # =====================================================================

        echo_lambda = lambda_.Function(
            self,
            "EchoConfigLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/echo_config"),
            timeout=Duration.seconds(30),
            memory_size=256,
            description="MVP: Echo configuration to test Step Functions connectivity",
        )

        # CloudWatch Logs for Lambda
        echo_lambda_logs = logs.LogGroup(
            self,
            "EchoLambdaLogGroup",
            log_group_name=f"/aws/lambda/{echo_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # =====================================================================
        # Step Functions State Machine
        # =====================================================================

        # Define the state machine using JSON definition
        # Simple one-state workflow: Pass input → Invoke Lambda → Return result
        definition = {
            "Comment": "MVP Evaluation Pipeline - Configuration Echo Test",
            "StartAt": "EchoConfiguration",
            "States": {
                "EchoConfiguration": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": echo_lambda.function_arn,
                        "Payload.$": "$"
                    },
                    "ResultSelector": {
                        "statusCode.$": "$.Payload.statusCode",
                        "body.$": "$.Payload"
                    },
                    "End": True
                }
            }
        }

        # Create IAM role
        state_machine_role = self._create_state_machine_role(echo_lambda)

        # Create state machine (without CloudWatch Logs for MVP simplicity)
        # Can add logging later once basic connectivity is verified
        state_machine = sfn.CfnStateMachine(
            self,
            "MvpEchoStateMachine",
            state_machine_name="evaluation-pipeline-mvp-echo",
            definition_string=json.dumps(definition),
            role_arn=state_machine_role.role_arn,
        )

        # =====================================================================
        # Stack Outputs
        # =====================================================================

        CfnOutput(
            self,
            "EchoLambdaArn",
            value=echo_lambda.function_arn,
            description="ARN of the configuration echo Lambda function",
            export_name=f"{self.stack_name}-EchoLambdaArn",
        )

        CfnOutput(
            self,
            "StateMachineArn",
            value=state_machine.attr_arn,
            description="ARN of the MVP Step Functions state machine",
            export_name=f"{self.stack_name}-StateMachineArn",
        )

        CfnOutput(
            self,
            "TestCommand",
            value=(
                f"aws stepfunctions start-execution "
                f"--state-machine-arn {state_machine.attr_arn} "
                f"--input file://config/test_mvp.yaml"
            ),
            description="Command to test the Step Functions workflow (requires converting YAML to JSON first)",
        )

    def _create_state_machine_role(self, echo_lambda: lambda_.Function) -> iam.Role:
        """Create IAM role for Step Functions state machine"""
        role = iam.Role(
            self,
            "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            description="Execution role for MVP evaluation pipeline state machine",
        )

        # Grant permission to invoke Lambda
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[echo_lambda.function_arn],
            )
        )

        return role

    def _create_state_machine_log_group(self, state_machine_role: iam.Role) -> logs.LogGroup:
        """Create CloudWatch log group for Step Functions execution logs"""
        log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            log_group_name="/aws/vendedlogs/states/evaluation-pipeline-mvp",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Grant Step Functions role permission to write logs
        # These are the required permissions for Step Functions CloudWatch Logs integration
        state_machine_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogDelivery",
                    "logs:GetLogDelivery",
                    "logs:UpdateLogDelivery",
                    "logs:DeleteLogDelivery",
                    "logs:ListLogDeliveries",
                    "logs:PutLogEvents",
                    "logs:PutResourcePolicy",
                    "logs:DescribeResourcePolicies",
                    "logs:DescribeLogGroups"
                ],
                resources=["*"],
            )
        )

        return log_group
