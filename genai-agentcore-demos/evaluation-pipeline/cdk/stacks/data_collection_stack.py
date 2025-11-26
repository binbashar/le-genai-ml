"""
Data Collection Stack for Evaluation Pipeline

Phase 1: CloudWatch → Firehose → S3 (bypass mode, no transformation)

Infrastructure components:
- CloudWatch Log Group (7-day retention, GDPR compliant)
- S3 bucket for raw data storage
- Kinesis Firehose stream for ETL
- IAM roles for Bedrock logging and Firehose delivery
"""

from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_kinesisfirehose as firehose,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct


class DataCollectionStack(Stack):
    """
    CDK stack for data collection infrastructure.

    Creates:
    - CloudWatch log group for Bedrock invocations
    - S3 bucket for staging data
    - Kinesis Firehose stream (CloudWatch → S3)
    - IAM roles with least-privilege permissions
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        enable_transformation: bool = False,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Stack configuration
        account = self.account
        region = self.region
        self.enable_transformation = enable_transformation

        # =====================================================================
        # CloudWatch Log Group
        # =====================================================================

        log_group = logs.LogGroup(
            self,
            "BedrockInvocationsLogGroup",
            log_group_name="bedrock-model-invocations",
            retention=logs.RetentionDays.ONE_WEEK,  # 7-day GDPR compliance
            removal_policy=RemovalPolicy.DESTROY,  # Clean deletion for dev
        )

        # =====================================================================
        # S3 Bucket for Data Storage
        # =====================================================================

        bucket = s3.Bucket(
            self,
            "EvaluationDataBucket",
            bucket_name=f"eval-pipeline-{account}-{region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # Clean deletion for dev
            auto_delete_objects=True,  # Delete contents on stack deletion
            lifecycle_rules=[
                # Phase 1: Auto-delete raw bypass data after 7 days
                s3.LifecycleRule(
                    id="DeleteRawDataAfter7Days",
                    prefix="raw/",
                    expiration=Duration.days(7),
                    enabled=True,
                ),
                # Future: staging/ data retained longer
                s3.LifecycleRule(
                    id="TransitionStagingToIA",
                    prefix="staging/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(30),
                        )
                    ],
                    enabled=False,  # Enable in Phase 2
                ),
            ],
        )

        # Store bucket name for cross-stack reference
        self.bucket_name = bucket.bucket_name

        # =====================================================================
        # IAM Role for Bedrock Model Invocation Logging
        # =====================================================================

        bedrock_logging_role = iam.Role(
            self,
            "BedrockLoggingRole",
            role_name=f"BedrockModelInvocationsLogging-{region}",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Allow Bedrock to write model invocation logs to CloudWatch (account-wide)",
        )

        # Grant Bedrock permission to write to CloudWatch
        bedrock_logging_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[log_group.log_group_arn],
            )
        )

        # =====================================================================
        # IAM Role for Kinesis Firehose
        # =====================================================================

        firehose_role = iam.Role(
            self,
            "FirehoseDeliveryRole",
            role_name=f"EvaluationPipeline-FirehoseDelivery-{region}",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
            description="Allow Firehose to read from CloudWatch Logs and write to S3",
        )

        # Grant Firehose permission to read from CloudWatch Logs
        firehose_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                ],
                resources=[log_group.log_group_arn],
            )
        )

        # Grant Firehose permission to write to S3
        bucket.grant_read_write(firehose_role)

        # =====================================================================
        # Lambda Transformation (Phase 2 - Optional)
        # =====================================================================

        transform_function = None
        if self.enable_transformation:
            # IAM role for Lambda execution
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

            # Create Lambda function (zip deployment without layers)
            # Note: PyArrow bundled with function code using pip install -t
            transform_function = lambda_.Function(
                self,
                "TransformBedrockLogsV2",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                architecture=lambda_.Architecture.X86_64,  # Ensure x86_64 bundling
                code=lambda_.Code.from_asset(
                    "lambda/transform_bedrock_logs",
                    bundling=BundlingOptions(
                        image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                        platform="linux/amd64",  # Force x86_64 platform for bundling
                        command=[
                            "bash", "-c",
                            "pip install --no-cache-dir -r requirements.txt -t /asset-output && "
                            "cp -au . /asset-output"
                        ],
                    ),
                ),
                timeout=Duration.minutes(3),  # Firehose maximum
                memory_size=512,
                role=lambda_role,
                environment={
                    "LOG_LEVEL": "INFO",
                    "PYTHONUNBUFFERED": "1",
                    "BUCKET_NAME": bucket.bucket_name,  # S3 bucket for Parquet writes
                },
                retry_attempts=2,
            )

            # Grant Lambda permission to write Parquet files to S3
            bucket.grant_write(transform_function)

            # Lambda CloudWatch Logs
            lambda_log_group = logs.LogGroup(
                self,
                "TransformLambdaLogGroup",
                log_group_name=f"/aws/lambda/{transform_function.function_name}",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            )

            # Grant Firehose permission to invoke Lambda
            transform_function.grant_invoke(iam.ServicePrincipal("firehose.amazonaws.com"))

            # Grant Firehose role permission to invoke Lambda
            firehose_role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["lambda:InvokeFunction"],
                    resources=[transform_function.function_arn],
                )
            )

        # =====================================================================
        # CloudWatch Logs Role for Firehose Subscription
        # =====================================================================

        logs_subscription_role = iam.Role(
            self,
            "LogsSubscriptionRole",
            role_name=f"EvaluationPipeline-LogsSubscription-{region}",
            assumed_by=iam.ServicePrincipal(f"logs.{region}.amazonaws.com"),
            description="Allow CloudWatch Logs to put records to Firehose",
        )

        logs_subscription_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["firehose:PutRecord", "firehose:PutRecordBatch"],
                resources=[
                    f"arn:aws:firehose:{region}:{account}:deliverystream/evaluation-pipeline-cloudwatch-to-s3"
                ],
            )
        )

        # =====================================================================
        # Kinesis Firehose Delivery Stream
        # =====================================================================

        # S3 destination configuration (with optional Lambda transformation)
        # Phase 1: raw/ prefix (bypass mode)
        # Phase 2: staging/ prefix (transformed with PII scrubbing)
        prefix = "staging/" if self.enable_transformation else "raw/"
        prefix += "year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"

        error_prefix = ("staging-failed/" if self.enable_transformation else "raw-failed/")
        error_prefix += "year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/!{firehose:error-output-type}/"

        # Processing configuration (Lambda transformation if enabled)
        processing_config = None
        if self.enable_transformation and transform_function:
            processing_config = firehose.CfnDeliveryStream.ProcessingConfigurationProperty(
                enabled=True,
                processors=[
                    firehose.CfnDeliveryStream.ProcessorProperty(
                        type="Lambda",
                        parameters=[
                            firehose.CfnDeliveryStream.ProcessorParameterProperty(
                                parameter_name="LambdaArn",
                                parameter_value=transform_function.function_arn,
                            ),
                            firehose.CfnDeliveryStream.ProcessorParameterProperty(
                                parameter_name="BufferSizeInMBs",
                                parameter_value="3",  # 3MB buffer
                            ),
                            firehose.CfnDeliveryStream.ProcessorParameterProperty(
                                parameter_name="BufferIntervalInSeconds",
                                parameter_value="60",  # 60s buffer
                            ),
                        ],
                    )
                ],
            )
        else:
            processing_config = firehose.CfnDeliveryStream.ProcessingConfigurationProperty(
                enabled=False
            )

        s3_destination = firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
            bucket_arn=bucket.bucket_arn,
            role_arn=firehose_role.role_arn,
            prefix=prefix,
            error_output_prefix=error_prefix,
            # Buffering configuration (fast for testing)
            buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                interval_in_seconds=60,  # 60s buffer (fast for testing)
                size_in_m_bs=1,  # 1MB buffer size
            ),
            # GZIP compression for storage efficiency
            compression_format="GZIP",
            # CloudWatch logging for delivery monitoring
            cloud_watch_logging_options=firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
                enabled=True,
                log_group_name="/aws/kinesisfirehose/evaluation-pipeline",
                log_stream_name="S3Delivery",
            ),
            # Data transformation (Lambda processor if enabled)
            processing_configuration=processing_config,
        )

        # Create Firehose delivery stream
        delivery_stream = firehose.CfnDeliveryStream(
            self,
            "FirehoseDeliveryStream",
            delivery_stream_name="evaluation-pipeline-cloudwatch-to-s3",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=s3_destination,
        )

        # =====================================================================
        # CloudWatch Logs Subscription Filter
        # =====================================================================

        # Subscribe Firehose to CloudWatch log group
        # This creates the connection: CloudWatch → Firehose → S3
        subscription_filter = logs.CfnSubscriptionFilter(
            self,
            "LogsToFirehoseSubscription",
            log_group_name=log_group.log_group_name,
            destination_arn=f"arn:aws:firehose:{region}:{account}:deliverystream/{delivery_stream.delivery_stream_name}",
            filter_pattern="",  # Empty = capture all logs
            role_arn=logs_subscription_role.role_arn,
        )

        # Ensure proper resource creation order
        subscription_filter.node.add_dependency(delivery_stream)
        subscription_filter.node.add_dependency(logs_subscription_role)

        # =====================================================================
        # CloudWatch Log Group for Firehose Monitoring
        # =====================================================================

        firehose_log_group = logs.LogGroup(
            self,
            "FirehoseLogGroup",
            log_group_name="/aws/kinesisfirehose/evaluation-pipeline",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        firehose_log_stream = logs.LogStream(
            self,
            "FirehoseLogStream",
            log_group=firehose_log_group,
            log_stream_name="S3Delivery",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Grant Firehose permission to write logs
        firehose_log_group.grant_write(firehose_role)

        # =====================================================================
        # Stack Outputs
        # =====================================================================

        CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="CloudWatch log group for Bedrock model invocations",
            export_name=f"{self.stack_name}-LogGroupName",
        )

        CfnOutput(
            self,
            "BucketName",
            value=bucket.bucket_name,
            description="S3 bucket for evaluation data",
            export_name=f"{self.stack_name}-BucketName",
        )

        CfnOutput(
            self,
            "FirehoseStreamName",
            value=delivery_stream.delivery_stream_name
            or "evaluation-pipeline-cloudwatch-to-s3",
            description="Kinesis Firehose delivery stream name",
            export_name=f"{self.stack_name}-FirehoseStreamName",
        )

        CfnOutput(
            self,
            "BedrockLoggingRoleArn",
            value=bedrock_logging_role.role_arn,
            description="IAM role ARN for Bedrock model invocation logging",
            export_name=f"{self.stack_name}-BedrockLoggingRoleArn",
        )

        CfnOutput(
            self,
            "ManualConfigCommand",
            value=(
                f"aws bedrock put-model-invocation-logging-configuration "
                f'--logging-config \'{{"cloudWatchConfig": {{"logGroupName": "{log_group.log_group_name}", '
                f'"roleArn": "{bedrock_logging_role.role_arn}"}}}}\''
            ),
            description="CLI command to configure Bedrock logging (run manually after stack creation)",
        )

        # Lambda transformation outputs (Phase 2)
        if self.enable_transformation and transform_function:
            CfnOutput(
                self,
                "TransformLambdaArn",
                value=transform_function.function_arn,
                description="Lambda function ARN for Firehose transformation",
                export_name=f"{self.stack_name}-TransformLambdaArn",
            )

            CfnOutput(
                self,
                "TransformLambdaName",
                value=transform_function.function_name,
                description="Lambda function name",
                export_name=f"{self.stack_name}-TransformLambdaName",
            )
