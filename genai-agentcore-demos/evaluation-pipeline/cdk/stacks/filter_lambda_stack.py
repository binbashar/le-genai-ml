"""
Filter Lambda Stack - Phase 4a: Data Gathering

Deploys the filter_gather_data Lambda function with necessary permissions.
This Lambda reads Parquet from staging and creates JSONL for evaluations.

Next Steps:
- Test this Lambda independently
- Add Step Functions orchestration once validated
- Add remaining Lambdas (validate, process, save)
"""

from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_ecr_assets as ecr_assets,
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
from constructs import Construct


class FilterLambdaStack(Stack):
    """
    Stack for deploying the filter_gather_data Lambda function.

    This Lambda is responsible for:
    1. Reading Parquet files from S3 staging
    2. Applying date and agent filters
    3. Sampling records (simple random for MVP)
    4. Transforming to Bedrock evaluation JSONL format
    5. Writing output to evaluation-datasets prefix
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        staging_bucket_name: str,
        **kwargs
    ) -> None:
        """
        Initialize the Filter Lambda stack.

        Args:
            scope: CDK scope
            construct_id: Stack ID
            staging_bucket_name: Name of S3 bucket with staging data
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.staging_bucket_name = staging_bucket_name
        region = self.region
        account = self.account

        # =====================================================================
        # Docker Image for Lambda
        # =====================================================================

        # Build Docker image from filter_gather_data directory
        lambda_dir = Path(__file__).parent.parent / "lambda" / "filter_gather_data"

        docker_image = ecr_assets.DockerImageAsset(
            self,
            "FilterGatherDataImage",
            directory=str(lambda_dir),
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        # =====================================================================
        # IAM Role for Lambda
        # =====================================================================

        lambda_role = self._create_lambda_role()

        # =====================================================================
        # Lambda Function
        # =====================================================================

        filter_lambda = lambda_.DockerImageFunction(
            self,
            "FilterGatherDataLambda",
            code=lambda_.DockerImageCode.from_ecr(
                repository=docker_image.repository,
                tag_or_digest=docker_image.image_tag
            ),
            timeout=Duration.seconds(300),  # 5 minutes
            memory_size=1024,  # 1GB for Parquet + pandas operations
            role=lambda_role,
            environment={
                "STAGING_BUCKET": staging_bucket_name,
            },
            description="Filter staging data and generate Bedrock evaluation datasets",
        )

        # CloudWatch Logs
        filter_lambda_logs = logs.LogGroup(
            self,
            "FilterLambdaLogGroup",
            log_group_name=f"/aws/lambda/{filter_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # =====================================================================
        # Store Lambda reference for other stacks
        # =====================================================================

        self.filter_lambda = filter_lambda

        # =====================================================================
        # Stack Outputs
        # =====================================================================

        CfnOutput(
            self,
            "FilterLambdaArn",
            value=filter_lambda.function_arn,
            description="ARN of the filter_gather_data Lambda function",
            export_name=f"{self.stack_name}-FilterLambdaArn",
        )

        CfnOutput(
            self,
            "FilterLambdaName",
            value=filter_lambda.function_name,
            description="Name of the filter_gather_data Lambda function",
            export_name=f"{self.stack_name}-FilterLambdaName",
        )

        CfnOutput(
            self,
            "TestCommand",
            value=(
                f"aws lambda invoke "
                f"--function-name {filter_lambda.function_name} "
                f"--payload '{{\n"
                f'  "agent_name":"finance-personal-assistant",\n'
                f'  "start_date":"2025-11-24",\n'
                f'  "end_date":"2025-11-24",\n'
                f'  "limit":10,\n'
                f'  "metrics":["Builtin.Correctness"]\n'
                f"}}' "
                f"response.json && cat response.json | jq ."
            ),
            description="Command to test the filter Lambda directly",
        )

    def _create_lambda_role(self) -> iam.Role:
        """
        Create IAM role for filter_gather_data Lambda.

        Permissions:
        - Read from staging/* (Parquet files)
        - Write to evaluation-datasets/* (JSONL files)
        - CloudWatch Logs
        """
        role = iam.Role(
            self,
            "FilterLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for filter_gather_data Lambda",
        )

        # CloudWatch Logs (managed policy)
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # S3 permissions
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:aws:s3:::{self.staging_bucket_name}",
                ],
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                ],
                resources=[
                    f"arn:aws:s3:::{self.staging_bucket_name}/staging/*",
                ],
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                ],
                resources=[
                    f"arn:aws:s3:::{self.staging_bucket_name}/evaluation-datasets/*",
                ],
            )
        )

        return role
