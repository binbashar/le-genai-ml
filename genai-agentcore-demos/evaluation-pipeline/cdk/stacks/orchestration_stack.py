"""
Orchestration Stack - Phase 5: Step Functions Integration

Integrates all Lambda functions into a unified Step Functions workflow.
Orchestrates: Filter → Create Eval Job → Poll Status → Process Results

Architecture:
┌─────────────┐
│   Input     │ Configuration (agent_name, date_range, metrics)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Filter Λ   │ Parquet → JSONL (evaluation-datasets/)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Create Job  │ CreateEvaluationJob API
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Poll      │ ← Wait 60s ← Status != Completed/Failed
│   Status    │
└──────┬──────┘
       │ (Completed)
       ↓
┌─────────────┐
│  Process    │ Extract metrics, write summary
│  Results    │
└─────────────┘
"""

import json
from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    Fn,
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


class OrchestrationStack(Stack):
    """
    Unified orchestration stack for evaluation pipeline.

    Integrates:
    - Filter Lambda (from FilterLambdaStack)
    - Create Evaluation Job Lambda (from EvaluationJobStack)
    - Poll Job Status Lambda (new)
    - Process Results Lambda (new)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        filter_lambda_arn: str,
        create_eval_lambda_arn: str,
        staging_bucket_name: str,
        **kwargs
    ) -> None:
        """
        Initialize the Orchestration stack.

        Args:
            scope: CDK scope
            construct_id: Stack ID
            filter_lambda_arn: ARN of filter Lambda
            create_eval_lambda_arn: ARN of create evaluation job Lambda
            staging_bucket_name: S3 bucket for evaluation data
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.staging_bucket_name = staging_bucket_name

        # =====================================================================
        # Poll Job Status Lambda
        # =====================================================================

        poll_status_lambda = self._create_poll_status_lambda()

        # =====================================================================
        # Process Results Lambda
        # =====================================================================

        process_results_lambda = self._create_process_results_lambda()

        # =====================================================================
        # Step Functions State Machine
        # =====================================================================

        state_machine_role = self._create_state_machine_role(
            filter_lambda_arn=filter_lambda_arn,
            create_eval_lambda_arn=create_eval_lambda_arn,
            poll_status_lambda=poll_status_lambda,
            process_results_lambda=process_results_lambda,
        )

        state_machine = self._create_state_machine(
            filter_lambda_arn=filter_lambda_arn,
            create_eval_lambda_arn=create_eval_lambda_arn,
            poll_status_lambda_arn=poll_status_lambda.function_arn,
            process_results_lambda_arn=process_results_lambda.function_arn,
            role=state_machine_role,
        )

        # =====================================================================
        # Outputs
        # =====================================================================

        CfnOutput(
            self,
            "StateMachineArn",
            value=state_machine.attr_arn,
            description="ARN of the evaluation pipeline Step Functions state machine",
            export_name=f"{self.stack_name}-StateMachineArn",
        )

        CfnOutput(
            self,
            "StateMachineName",
            value=state_machine.state_machine_name,
            description="Name of the evaluation pipeline state machine",
        )

        CfnOutput(
            self,
            "TestCommand",
            value=(
                f"aws stepfunctions start-execution "
                f"--state-machine-arn {state_machine.attr_arn} "
                f"--input '{{\"agent_name\":\"claude-sonnet\",\"start_date\":\"2025-11-25\",\"end_date\":\"2025-11-25\",\"limit\":10,\"metrics\":[\"Builtin.Correctness\"]}}'"
            ),
            description="Command to test the evaluation pipeline",
        )

    def _create_poll_status_lambda(self) -> lambda_.Function:
        """Create Lambda for polling Bedrock evaluation job status."""
        lambda_dir = Path(__file__).parent.parent / "lambda" / "poll_job_status"

        poll_lambda = lambda_.Function(
            self,
            "PollJobStatusLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(str(lambda_dir)),
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Poll Bedrock evaluation job status",
        )

        # CloudWatch Logs
        logs.LogGroup(
            self,
            "PollStatusLogGroup",
            log_group_name=f"/aws/lambda/{poll_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Grant Bedrock GetEvaluationJob permission
        poll_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockGetEvaluationJob",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:GetEvaluationJob"],
                resources=["*"],
            )
        )

        return poll_lambda

    def _create_process_results_lambda(self) -> lambda_.Function:
        """Create Lambda for processing evaluation results."""
        lambda_dir = Path(__file__).parent.parent / "lambda" / "process_results"

        process_lambda = lambda_.Function(
            self,
            "ProcessResultsLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(str(lambda_dir)),
            timeout=Duration.seconds(300),  # 5 minutes for S3 operations
            memory_size=512,
            environment={
                "STAGING_BUCKET": self.staging_bucket_name,
            },
            description="Process evaluation job results and extract metrics",
        )

        # CloudWatch Logs
        logs.LogGroup(
            self,
            "ProcessResultsLogGroup",
            log_group_name=f"/aws/lambda/{process_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Grant S3 permissions
        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="S3ReadResults",
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:::{self.staging_bucket_name}",
                    f"arn:aws:s3:::{self.staging_bucket_name}/evaluation-results/*",
                ],
            )
        )

        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="S3WriteSummary",
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[
                    f"arn:aws:s3:::{self.staging_bucket_name}/evaluation-results/*",
                ],
            )
        )

        return process_lambda

    def _create_state_machine_role(
        self,
        filter_lambda_arn: str,
        create_eval_lambda_arn: str,
        poll_status_lambda: lambda_.Function,
        process_results_lambda: lambda_.Function,
    ) -> iam.Role:
        """Create IAM role for Step Functions state machine."""
        role = iam.Role(
            self,
            "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            description="Execution role for evaluation pipeline state machine",
        )

        # Grant permission to invoke all Lambdas
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    filter_lambda_arn,
                    create_eval_lambda_arn,
                    poll_status_lambda.function_arn,
                    process_results_lambda.function_arn,
                ],
            )
        )

        # CloudWatch Logs permissions for Step Functions
        role.add_to_policy(
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
                    "logs:DescribeLogGroups",
                ],
                resources=["*"],
            )
        )

        return role

    def _create_state_machine(
        self,
        filter_lambda_arn: str,
        create_eval_lambda_arn: str,
        poll_status_lambda_arn: str,
        process_results_lambda_arn: str,
        role: iam.Role,
    ) -> sfn.CfnStateMachine:
        """Create Step Functions state machine with polling pattern."""

        # State machine definition using Amazon States Language
        definition = {
            "Comment": "Evaluation Pipeline - Filter, Evaluate, Poll, Process",
            "StartAt": "FilterData",
            "States": {
                # Step 1: Filter staging data and create JSONL dataset
                "FilterData": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": filter_lambda_arn,
                        "Payload.$": "$"
                    },
                    "ResultSelector": {
                        "dataset_s3_uri.$": "$.Payload.dataset_s3_uri",
                        "question_count.$": "$.Payload.question_count",
                        "sampling_stats.$": "$.Payload.sampling_stats"
                    },
                    "ResultPath": "$.filter_result",
                    "Next": "PrepareEvalJobInput",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "FilterFailed",
                            "ResultPath": "$.error"
                        }
                    ]
                },

                # Merge filter results with original input for eval job
                "PrepareEvalJobInput": {
                    "Type": "Pass",
                    "Parameters": {
                        "dataset_s3_uri.$": "$.filter_result.dataset_s3_uri",
                        "question_count.$": "$.filter_result.question_count",
                        "agent_name.$": "$.agent_name",
                        "metrics.$": "$.metrics"
                    },
                    "Next": "CreateEvaluationJob"
                },

                # Step 2: Create Bedrock evaluation job
                "CreateEvaluationJob": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": create_eval_lambda_arn,
                        "Payload.$": "$"
                    },
                    "ResultSelector": {
                        "job_arn.$": "$.Payload.job_arn",
                        "job_name.$": "$.Payload.job_name",
                        "status.$": "$.Payload.status",
                        "dataset_s3_uri.$": "$.Payload.dataset_s3_uri",
                        "output_s3_uri.$": "$.Payload.output_s3_uri",
                        "question_count.$": "$.Payload.question_count",
                        "metrics.$": "$.Payload.metrics",
                        "judge_model_id.$": "$.Payload.judge_model_id",
                        "agent_name.$": "$.Payload.agent_name"
                    },
                    "ResultPath": "$.eval_job",
                    "Next": "WaitForJob",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 10,
                            "MaxAttempts": 2,
                            "BackoffRate": 2
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "CreateJobFailed",
                            "ResultPath": "$.error"
                        }
                    ]
                },

                # Wait before polling (Bedrock jobs take several minutes)
                "WaitForJob": {
                    "Type": "Wait",
                    "Seconds": 60,
                    "Next": "PollJobStatus"
                },

                # Step 3: Poll job status
                "PollJobStatus": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": poll_status_lambda_arn,
                        "Payload.$": "$.eval_job"
                    },
                    "ResultSelector": {
                        "job_arn.$": "$.Payload.job_arn",
                        "job_name.$": "$.Payload.job_name",
                        "status.$": "$.Payload.status",
                        "dataset_s3_uri.$": "$.Payload.dataset_s3_uri",
                        "output_s3_uri.$": "$.Payload.output_s3_uri",
                        "question_count.$": "$.Payload.question_count",
                        "metrics.$": "$.Payload.metrics",
                        "failure_reasons.$": "$.Payload.failure_reasons",
                        "agent_name.$": "$.Payload.agent_name"
                    },
                    "ResultPath": "$.eval_job",
                    "Next": "CheckJobStatus",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 3,
                            "BackoffRate": 2
                        }
                    ]
                },

                # Check if job is complete, failed, or still running
                "CheckJobStatus": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.eval_job.status",
                            "StringEquals": "Completed",
                            "Next": "ProcessResults"
                        },
                        {
                            "Variable": "$.eval_job.status",
                            "StringEquals": "Failed",
                            "Next": "JobFailed"
                        },
                        {
                            "Variable": "$.eval_job.status",
                            "StringEquals": "Stopped",
                            "Next": "JobStopped"
                        }
                    ],
                    "Default": "WaitForJob"
                },

                # Step 4: Process completed results
                "ProcessResults": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": process_results_lambda_arn,
                        "Payload.$": "$.eval_job"
                    },
                    "ResultSelector": {
                        "job_arn.$": "$.Payload.job_arn",
                        "job_name.$": "$.Payload.job_name",
                        "agent_name.$": "$.Payload.agent_name",
                        "results.$": "$.Payload.results"
                    },
                    "ResultPath": "$.final_results",
                    "Next": "Success",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "ProcessingFailed",
                            "ResultPath": "$.error"
                        }
                    ]
                },

                # Success state
                "Success": {
                    "Type": "Succeed"
                },

                # Error states
                "FilterFailed": {
                    "Type": "Fail",
                    "Error": "FilterDataFailed",
                    "Cause": "Failed to filter and prepare evaluation dataset"
                },

                "CreateJobFailed": {
                    "Type": "Fail",
                    "Error": "CreateEvaluationJobFailed",
                    "Cause": "Failed to create Bedrock evaluation job"
                },

                "JobFailed": {
                    "Type": "Fail",
                    "Error": "EvaluationJobFailed",
                    "Cause": "Bedrock evaluation job failed"
                },

                "JobStopped": {
                    "Type": "Fail",
                    "Error": "EvaluationJobStopped",
                    "Cause": "Bedrock evaluation job was stopped"
                },

                "ProcessingFailed": {
                    "Type": "Fail",
                    "Error": "ProcessResultsFailed",
                    "Cause": "Failed to process evaluation results"
                }
            }
        }

        # Create log group for state machine
        log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            log_group_name="/aws/vendedlogs/states/evaluation-pipeline",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        state_machine = sfn.CfnStateMachine(
            self,
            "EvaluationPipelineStateMachine",
            state_machine_name="evaluation-pipeline",
            definition_string=json.dumps(definition),
            role_arn=role.role_arn,
            state_machine_type="STANDARD",
            logging_configuration=sfn.CfnStateMachine.LoggingConfigurationProperty(
                destinations=[
                    sfn.CfnStateMachine.LogDestinationProperty(
                        cloud_watch_logs_log_group=sfn.CfnStateMachine.CloudWatchLogsLogGroupProperty(
                            log_group_arn=log_group.log_group_arn
                        )
                    )
                ],
                include_execution_data=True,
                level="ALL"
            ),
            tracing_configuration=sfn.CfnStateMachine.TracingConfigurationProperty(
                enabled=True
            ),
        )

        return state_machine
