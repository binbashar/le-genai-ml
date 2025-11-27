"""
Evaluation Pipeline Stack

- Data Collection: CloudWatch → Firehose → S3 with Lambda transformation
- Filter Lambda: Parquet → JSONL for Bedrock evaluation
- Evaluation Job: Create Bedrock evaluation jobs
- Orchestration: Step Functions workflow

Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EvaluationPipelineStack                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Data Collection (continuous):                                              │
│    Bedrock → CloudWatch → Firehose → Transform Lambda → S3 (Parquet)        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Evaluation (on-demand via Step Functions):                                 │
│    Input → Filter Lambda → Create Eval Job → Poll Status → Process Results  │
└─────────────────────────────────────────────────────────────────────────────┘

Deployment:
    cd cdk
    AWS_PROFILE=binbash uv run cdk deploy EvaluationPipeline --require-approval never

    # After deployment, configure Bedrock logging (one-time):
    # Run the command from ManualConfigCommand output
"""

import json
from pathlib import Path

from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kinesisfirehose as firehose
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_stepfunctions as sfn
from constructs import Construct


class EvaluationPipelineStack(Stack):
    """
    CDK stack for the evaluation pipeline.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        deploy_orchestration: bool = True,
        **kwargs,
    ) -> None:
        """
        Initialize the Evaluation Pipeline stack.

        Args:
            scope: CDK scope
            construct_id: Stack ID
            deploy_orchestration: Whether to deploy Step Functions (default: True)
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.deploy_orchestration = deploy_orchestration

        # =====================================================================
        # 1. Base Infrastructure (S3, CloudWatch, IAM)
        # =====================================================================

        self._create_base_infrastructure()

        # =====================================================================
        # 2. Transform Lambda (Firehose → Parquet)
        # =====================================================================

        self._create_transform_lambda()

        # =====================================================================
        # 3. Firehose Delivery Stream
        # =====================================================================

        self._create_firehose_stream()

        # =====================================================================
        # 4. Filter Lambda (Parquet → JSONL)
        # =====================================================================

        self._create_filter_lambda()

        # =====================================================================
        # 5. Evaluation Job Lambda
        # =====================================================================

        self._create_evaluation_job_lambda()

        # =====================================================================
        # 6. Orchestration (Step Functions)
        # =====================================================================

        if self.deploy_orchestration:
            self._create_orchestration()

        # =====================================================================
        # 7. Stack Outputs
        # =====================================================================

        self._create_outputs()

    # =========================================================================
    # Base Infrastructure
    # =========================================================================

    def _create_base_infrastructure(self) -> None:
        """Create S3 bucket, CloudWatch log group, and IAM roles."""
        account = self.account
        region = self.region

        # CloudWatch Log Group for Bedrock invocations
        self.log_group = logs.LogGroup(
            self,
            "BedrockInvocationsLogGroup",
            log_group_name="bedrock-model-invocations",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # S3 Bucket for all pipeline data
        self.bucket = s3.Bucket(
            self,
            "EvaluationDataBucket",
            bucket_name=f"eval-pipeline-{account}-{region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteRawDataAfter7Days",
                    prefix="raw/",
                    expiration=Duration.days(7),
                    enabled=True,
                ),
            ],
        )

        # IAM Role for Bedrock Model Invocation Logging
        self.bedrock_logging_role = iam.Role(
            self,
            "BedrockLoggingRole",
            role_name=f"BedrockModelInvocationsLogging-{region}",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Allow Bedrock to write model invocation logs to CloudWatch",
        )

        self.bedrock_logging_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[self.log_group.log_group_arn],
            )
        )

        # IAM Role for Firehose
        self.firehose_role = iam.Role(
            self,
            "FirehoseDeliveryRole",
            role_name=f"EvaluationPipeline-FirehoseDelivery-{region}",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
            description="Allow Firehose to read from CloudWatch and write to S3",
        )

        self.firehose_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:DescribeLogStreams", "logs:GetLogEvents"],
                resources=[self.log_group.log_group_arn],
            )
        )
        self.bucket.grant_read_write(self.firehose_role)

        # CloudWatch Logs Role for Firehose Subscription
        self.logs_subscription_role = iam.Role(
            self,
            "LogsSubscriptionRole",
            role_name=f"EvaluationPipeline-LogsSubscription-{region}",
            assumed_by=iam.ServicePrincipal(f"logs.{region}.amazonaws.com"),
            description="Allow CloudWatch Logs to put records to Firehose",
        )

        self.logs_subscription_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["firehose:PutRecord", "firehose:PutRecordBatch"],
                resources=[
                    f"arn:aws:firehose:{region}:{account}:deliverystream/evaluation-pipeline-cloudwatch-to-s3"
                ],
            )
        )

    # =========================================================================
    # Transform Lambda
    # =========================================================================

    def _create_transform_lambda(self) -> None:
        """Create Lambda for transforming Firehose records to Parquet."""
        region = self.region

        lambda_role = iam.Role(
            self,
            "TransformLambdaRole",
            role_name=f"EvaluationPipeline-TransformLambda-{region}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Bedrock log transformation Lambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        self.transform_lambda = lambda_.Function(
            self,
            "TransformBedrockLogs",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            architecture=lambda_.Architecture.X86_64,
            code=lambda_.Code.from_asset(
                "lambda/transform_bedrock_logs",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    platform="linux/amd64",
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache-dir -r requirements.txt -t /asset-output && "
                        "cp -au . /asset-output",
                    ],
                ),
            ),
            timeout=Duration.minutes(3),
            memory_size=512,
            role=lambda_role,
            environment={
                "LOG_LEVEL": "INFO",
                "PYTHONUNBUFFERED": "1",
                "BUCKET_NAME": self.bucket.bucket_name,
            },
            retry_attempts=2,
        )

        self.bucket.grant_write(self.transform_lambda)

        logs.LogGroup(
            self,
            "TransformLambdaLogGroup",
            log_group_name=f"/aws/lambda/{self.transform_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Grant Firehose permission to invoke Lambda
        self.transform_lambda.grant_invoke(
            iam.ServicePrincipal("firehose.amazonaws.com")
        )
        self.firehose_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[self.transform_lambda.function_arn],
            )
        )

    # =========================================================================
    # Firehose Delivery Stream
    # =========================================================================

    def _create_firehose_stream(self) -> None:
        """Create Firehose delivery stream with Lambda transformation."""
        account = self.account
        region = self.region

        # S3 destination with Lambda transformation
        prefix = "staging/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
        error_prefix = "staging-failed/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/!{firehose:error-output-type}/"

        processing_config = firehose.CfnDeliveryStream.ProcessingConfigurationProperty(
            enabled=True,
            processors=[
                firehose.CfnDeliveryStream.ProcessorProperty(
                    type="Lambda",
                    parameters=[
                        firehose.CfnDeliveryStream.ProcessorParameterProperty(
                            parameter_name="LambdaArn",
                            parameter_value=self.transform_lambda.function_arn,
                        ),
                        firehose.CfnDeliveryStream.ProcessorParameterProperty(
                            parameter_name="BufferSizeInMBs",
                            parameter_value="3",
                        ),
                        firehose.CfnDeliveryStream.ProcessorParameterProperty(
                            parameter_name="BufferIntervalInSeconds",
                            parameter_value="60",
                        ),
                    ],
                )
            ],
        )

        s3_destination = firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
            bucket_arn=self.bucket.bucket_arn,
            role_arn=self.firehose_role.role_arn,
            prefix=prefix,
            error_output_prefix=error_prefix,
            buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                interval_in_seconds=60,
                size_in_m_bs=1,
            ),
            compression_format="GZIP",
            cloud_watch_logging_options=firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
                enabled=True,
                log_group_name="/aws/kinesisfirehose/evaluation-pipeline",
                log_stream_name="S3Delivery",
            ),
            processing_configuration=processing_config,
        )

        self.delivery_stream = firehose.CfnDeliveryStream(
            self,
            "FirehoseDeliveryStream",
            delivery_stream_name="evaluation-pipeline-cloudwatch-to-s3",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=s3_destination,
        )

        # CloudWatch Logs subscription filter
        subscription_filter = logs.CfnSubscriptionFilter(
            self,
            "LogsToFirehoseSubscription",
            log_group_name=self.log_group.log_group_name,
            destination_arn=f"arn:aws:firehose:{region}:{account}:deliverystream/{self.delivery_stream.delivery_stream_name}",
            filter_pattern="",
            role_arn=self.logs_subscription_role.role_arn,
        )
        subscription_filter.node.add_dependency(self.delivery_stream)
        subscription_filter.node.add_dependency(self.logs_subscription_role)

        # Firehose monitoring log group
        firehose_log_group = logs.LogGroup(
            self,
            "FirehoseLogGroup",
            log_group_name="/aws/kinesisfirehose/evaluation-pipeline",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        logs.LogStream(
            self,
            "FirehoseLogStream",
            log_group=firehose_log_group,
            log_stream_name="S3Delivery",
            removal_policy=RemovalPolicy.DESTROY,
        )

        firehose_log_group.grant_write(self.firehose_role)

    # =========================================================================
    # Filter Lambda
    # =========================================================================

    def _create_filter_lambda(self) -> None:
        """Create Lambda for filtering Parquet and generating JSONL."""
        lambda_dir = Path(__file__).parent.parent / "lambda" / "filter_gather_data"

        docker_image = ecr_assets.DockerImageAsset(
            self,
            "FilterGatherDataImage",
            directory=str(lambda_dir),
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        filter_role = iam.Role(
            self,
            "FilterLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for filter_gather_data Lambda",
        )

        filter_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # S3 permissions
        filter_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket"],
                resources=[self.bucket.bucket_arn],
            )
        )
        filter_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=[f"{self.bucket.bucket_arn}/staging/*"],
            )
        )
        filter_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[f"{self.bucket.bucket_arn}/evaluation-datasets/*"],
            )
        )

        self.filter_lambda = lambda_.DockerImageFunction(
            self,
            "FilterGatherDataLambda",
            code=lambda_.DockerImageCode.from_ecr(
                repository=docker_image.repository, tag_or_digest=docker_image.image_tag
            ),
            timeout=Duration.seconds(300),
            memory_size=1024,
            role=filter_role,
            environment={"STAGING_BUCKET": self.bucket.bucket_name},
            description="Filter staging data and generate Bedrock evaluation datasets",
        )

        logs.LogGroup(
            self,
            "FilterLambdaLogGroup",
            log_group_name=f"/aws/lambda/{self.filter_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

    # =========================================================================
    # Evaluation Job Lambda
    # =========================================================================

    def _create_evaluation_job_lambda(self) -> None:
        """Create Lambda for creating Bedrock evaluation jobs."""
        region = self.region
        account = self.account

        # IAM Role for Bedrock evaluation jobs (assumed by Bedrock)
        self.evaluation_job_role = iam.Role(
            self,
            "EvaluationJobRole",
            role_name=f"EvaluationPipelineJobRole-{region}",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="IAM role for Bedrock model evaluation jobs",
        )

        self.evaluation_job_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3BucketAccess",
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket"],
                resources=[self.bucket.bucket_arn],
            )
        )

        self.evaluation_job_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ObjectAccess",
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:PutObject"],
                resources=[
                    f"{self.bucket.bucket_arn}/evaluation-datasets/*",
                    f"{self.bucket.bucket_arn}/evaluation-results/*",
                ],
            )
        )

        self.evaluation_job_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockModelAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{region}::foundation-model/amazon.nova-pro-v1:0",
                    "arn:aws:bedrock:*::foundation-model/amazon.nova-pro*",
                    "arn:aws:bedrock:*:*:inference-profile/us.amazon.nova-pro-v1:0",
                ],
            )
        )

        # Lambda for creating evaluation jobs
        lambda_dir = Path(__file__).parent.parent / "lambda" / "create_evaluation_job"

        self.create_eval_lambda = lambda_.Function(
            self,
            "CreateEvaluationJobLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(str(lambda_dir)),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "STAGING_BUCKET": self.bucket.bucket_name,
                "EVALUATION_ROLE_ARN": self.evaluation_job_role.role_arn,
                "JUDGE_MODEL_ID": "us.amazon.nova-pro-v1:0",
                "MAX_EVALUATION_SAMPLES": "10",
            },
            description="Create Bedrock model evaluation jobs",
        )

        self.create_eval_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        self.create_eval_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockCreateEvaluationJob",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:CreateEvaluationJob"],
                resources=["*"],
            )
        )

        self.create_eval_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="PassRoleToBedrock",
                effect=iam.Effect.ALLOW,
                actions=["iam:PassRole"],
                resources=[self.evaluation_job_role.role_arn],
                conditions={
                    "StringEquals": {"iam:PassedToService": "bedrock.amazonaws.com"}
                },
            )
        )

        logs.LogGroup(
            self,
            "CreateEvalLambdaLogGroup",
            log_group_name=f"/aws/lambda/{self.create_eval_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

    # =========================================================================
    # Orchestration (Step Functions)
    # =========================================================================

    def _create_orchestration(self) -> None:
        """Create Step Functions workflow and supporting Lambdas."""
        # Poll Status Lambda
        poll_lambda_dir = Path(__file__).parent.parent / "lambda" / "poll_job_status"

        self.poll_lambda = lambda_.Function(
            self,
            "PollJobStatusLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(str(poll_lambda_dir)),
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Poll Bedrock evaluation job status",
        )

        logs.LogGroup(
            self,
            "PollStatusLogGroup",
            log_group_name=f"/aws/lambda/{self.poll_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.poll_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockGetEvaluationJob",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:GetEvaluationJob"],
                resources=["*"],
            )
        )

        # Process Results Lambda
        process_lambda_dir = Path(__file__).parent.parent / "lambda" / "process_results"

        self.process_lambda = lambda_.Function(
            self,
            "ProcessResultsLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(str(process_lambda_dir)),
            timeout=Duration.seconds(300),
            memory_size=512,
            environment={"STAGING_BUCKET": self.bucket.bucket_name},
            description="Process evaluation job results and extract metrics",
        )

        logs.LogGroup(
            self,
            "ProcessResultsLogGroup",
            log_group_name=f"/aws/lambda/{self.process_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="S3ReadResults",
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    self.bucket.bucket_arn,
                    f"{self.bucket.bucket_arn}/evaluation-results/*",
                ],
            )
        )

        self.process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="S3WriteSummary",
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[f"{self.bucket.bucket_arn}/evaluation-results/*"],
            )
        )

        # Step Functions State Machine
        self._create_state_machine()

    def _create_state_machine(self) -> None:
        """Create Step Functions state machine."""
        # State Machine IAM Role
        state_machine_role = iam.Role(
            self,
            "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            description="Execution role for evaluation pipeline state machine",
        )

        state_machine_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    self.filter_lambda.function_arn,
                    self.create_eval_lambda.function_arn,
                    self.poll_lambda.function_arn,
                    self.process_lambda.function_arn,
                ],
            )
        )

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
                    "logs:DescribeLogGroups",
                ],
                resources=["*"],
            )
        )

        # State Machine Definition (ASL)
        definition = {
            "Comment": "Evaluation Pipeline - Filter, Evaluate, Poll, Process",
            "StartAt": "FilterData",
            "States": {
                "FilterData": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": self.filter_lambda.function_arn,
                        "Payload.$": "$",
                    },
                    "ResultSelector": {
                        "dataset_s3_uri.$": "$.Payload.dataset_s3_uri",
                        "question_count.$": "$.Payload.question_count",
                        "sampling_stats.$": "$.Payload.sampling_stats",
                    },
                    "ResultPath": "$.filter_result",
                    "Next": "CheckDataAvailable",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2,
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "FilterFailed",
                            "ResultPath": "$.error",
                        }
                    ],
                },
                "CheckDataAvailable": {
                    "Type": "Choice",
                    "Comment": "Check if filter found any data to evaluate",
                    "Choices": [
                        {
                            "Variable": "$.filter_result.question_count",
                            "NumericGreaterThan": 0,
                            "Next": "PrepareEvalJobInput",
                        }
                    ],
                    "Default": "FormatNoDataResponse",
                },
                "FormatNoDataResponse": {
                    "Type": "Pass",
                    "Comment": "Format response for no data found case",
                    "Parameters": {
                        "status": "NO_DATA_FOUND",
                        "message": "No traces found for the given filter configuration",
                        "filter_config": {
                            "agent_name.$": "$.agent_name",
                            "start_date.$": "$.start_date",
                            "end_date.$": "$.end_date",
                            "limit.$": "$.limit",
                            "metrics.$": "$.metrics",
                        },
                        "filter_result.$": "$.filter_result",
                    },
                    "Next": "NoDataFound",
                },
                "NoDataFound": {
                    "Type": "Succeed",
                    "Comment": "Evaluation completed - no data found for filter criteria",
                },
                "PrepareEvalJobInput": {
                    "Type": "Pass",
                    "Parameters": {
                        "dataset_s3_uri.$": "$.filter_result.dataset_s3_uri",
                        "question_count.$": "$.filter_result.question_count",
                        "agent_name.$": "$.agent_name",
                        "metrics.$": "$.metrics",
                    },
                    "Next": "CreateEvaluationJob",
                },
                "CreateEvaluationJob": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": self.create_eval_lambda.function_arn,
                        "Payload.$": "$",
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
                        "agent_name.$": "$.Payload.agent_name",
                    },
                    "ResultPath": "$.eval_job",
                    "Next": "WaitForJob",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 10,
                            "MaxAttempts": 2,
                            "BackoffRate": 2,
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "CreateJobFailed",
                            "ResultPath": "$.error",
                        }
                    ],
                },
                "WaitForJob": {"Type": "Wait", "Seconds": 60, "Next": "PollJobStatus"},
                "PollJobStatus": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": self.poll_lambda.function_arn,
                        "Payload.$": "$.eval_job",
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
                        "agent_name.$": "$.Payload.agent_name",
                    },
                    "ResultPath": "$.eval_job",
                    "Next": "CheckJobStatus",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 3,
                            "BackoffRate": 2,
                        }
                    ],
                },
                "CheckJobStatus": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.eval_job.status",
                            "StringEquals": "Completed",
                            "Next": "ProcessResults",
                        },
                        {
                            "Variable": "$.eval_job.status",
                            "StringEquals": "Failed",
                            "Next": "JobFailed",
                        },
                        {
                            "Variable": "$.eval_job.status",
                            "StringEquals": "Stopped",
                            "Next": "JobStopped",
                        },
                    ],
                    "Default": "WaitForJob",
                },
                "ProcessResults": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                        "FunctionName": self.process_lambda.function_arn,
                        "Payload.$": "$.eval_job",
                    },
                    "ResultSelector": {
                        "job_arn.$": "$.Payload.job_arn",
                        "job_name.$": "$.Payload.job_name",
                        "agent_name.$": "$.Payload.agent_name",
                        "results.$": "$.Payload.results",
                    },
                    "ResultPath": "$.final_results",
                    "Next": "Success",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 5,
                            "MaxAttempts": 2,
                            "BackoffRate": 2,
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "ProcessingFailed",
                            "ResultPath": "$.error",
                        }
                    ],
                },
                "Success": {"Type": "Succeed"},
                "FilterFailed": {
                    "Type": "Fail",
                    "Error": "FilterDataFailed",
                    "Cause": "Failed to filter and prepare evaluation dataset",
                },
                "CreateJobFailed": {
                    "Type": "Fail",
                    "Error": "CreateEvaluationJobFailed",
                    "Cause": "Failed to create Bedrock evaluation job",
                },
                "JobFailed": {
                    "Type": "Fail",
                    "Error": "EvaluationJobFailed",
                    "Cause": "Bedrock evaluation job failed",
                },
                "JobStopped": {
                    "Type": "Fail",
                    "Error": "EvaluationJobStopped",
                    "Cause": "Bedrock evaluation job was stopped",
                },
                "ProcessingFailed": {
                    "Type": "Fail",
                    "Error": "ProcessResultsFailed",
                    "Cause": "Failed to process evaluation results",
                },
            },
        }

        # Log group for state machine
        sfn_log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            log_group_name="/aws/vendedlogs/states/evaluation-pipeline",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Grant the state machine role permission to write to the log group
        sfn_log_group.grant_write(state_machine_role)

        self.state_machine = sfn.CfnStateMachine(
            self,
            "EvaluationPipelineStateMachine",
            state_machine_name="evaluation-pipeline",
            definition_string=json.dumps(definition),
            role_arn=state_machine_role.role_arn,
            state_machine_type="STANDARD",
            logging_configuration=sfn.CfnStateMachine.LoggingConfigurationProperty(
                destinations=[
                    sfn.CfnStateMachine.LogDestinationProperty(
                        cloud_watch_logs_log_group=sfn.CfnStateMachine.CloudWatchLogsLogGroupProperty(
                            log_group_arn=sfn_log_group.log_group_arn
                        )
                    )
                ],
                include_execution_data=True,
                level="ALL",
            ),
            tracing_configuration=sfn.CfnStateMachine.TracingConfigurationProperty(
                enabled=True
            ),
        )

        # Add explicit dependencies to ensure log group and permissions exist first
        self.state_machine.node.add_dependency(sfn_log_group)
        self.state_machine.node.add_dependency(state_machine_role)

    # =========================================================================
    # Stack Outputs
    # =========================================================================

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        region = self.region

        CfnOutput(
            self,
            "LogGroupName",
            value=self.log_group.log_group_name,
            description="CloudWatch log group for Bedrock model invocations",
        )

        CfnOutput(
            self,
            "BucketName",
            value=self.bucket.bucket_name,
            description="S3 bucket for evaluation data",
        )

        CfnOutput(
            self,
            "FirehoseStreamName",
            value=self.delivery_stream.delivery_stream_name
            or "evaluation-pipeline-cloudwatch-to-s3",
            description="Kinesis Firehose delivery stream name",
        )

        CfnOutput(
            self,
            "BedrockLoggingRoleArn",
            value=self.bedrock_logging_role.role_arn,
            description="IAM role ARN for Bedrock model invocation logging",
        )

        CfnOutput(
            self,
            "ManualConfigCommand",
            value=(
                f"aws bedrock put-model-invocation-logging-configuration "
                f'--logging-config \'{{"cloudWatchConfig": {{"logGroupName": "{self.log_group.log_group_name}", '
                f'"roleArn": "{self.bedrock_logging_role.role_arn}"}}}}\''
            ),
            description="CLI command to configure Bedrock logging (run manually after stack creation)",
        )

        CfnOutput(
            self,
            "TransformLambdaArn",
            value=self.transform_lambda.function_arn,
            description="Lambda function ARN for Firehose transformation",
        )

        CfnOutput(
            self,
            "FilterLambdaArn",
            value=self.filter_lambda.function_arn,
            description="ARN of the filter_gather_data Lambda function",
        )

        CfnOutput(
            self,
            "CreateEvalLambdaArn",
            value=self.create_eval_lambda.function_arn,
            description="ARN of the create_evaluation_job Lambda function",
        )

        CfnOutput(
            self,
            "EvaluationJobRoleArn",
            value=self.evaluation_job_role.role_arn,
            description="ARN of the IAM role for Bedrock evaluation jobs",
        )

        if self.deploy_orchestration:
            CfnOutput(
                self,
                "StateMachineArn",
                value=self.state_machine.attr_arn,
                description="ARN of the evaluation pipeline Step Functions state machine",
            )

            CfnOutput(
                self,
                "TestCommand",
                value=(
                    f"aws stepfunctions start-execution "
                    f"--state-machine-arn {self.state_machine.attr_arn} "
                    f'--input \'{{"agent_name":"claude-sonnet","start_date":"2025-11-25","end_date":"2025-11-25","limit":10,"metrics":["Builtin.Correctness"]}}\''
                ),
                description="Command to test the evaluation pipeline",
            )
