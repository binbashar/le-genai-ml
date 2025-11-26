"""
Evaluation Job Stack - Phase 4b: Create Bedrock Evaluation Jobs

Deploys the create_evaluation_job Lambda function with necessary permissions.
This Lambda creates Bedrock model evaluation jobs using filtered datasets.

Components:
- Lambda function: Creates Bedrock evaluation jobs via CreateEvaluationJob API
- IAM role: Allows Lambda to invoke Bedrock CreateEvaluationJob
- Evaluation role: IAM role for Bedrock evaluation jobs (S3 + model access)

Prerequisites:
- FilterLambdaStack deployed (provides dataset generation)
- S3 bucket with evaluation datasets

Next Steps:
- Add poll_job_status Lambda
- Add process_results Lambda
- Integrate into Step Functions workflow
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


class EvaluationJobStack(Stack):
    """
    Stack for deploying the create_evaluation_job Lambda function.

    This Lambda is responsible for:
    1. Receiving dataset S3 URI from previous step
    2. Creating Bedrock evaluation jobs via CreateEvaluationJob API
    3. Using model-as-judge pattern with Nova Pro
    4. Returning job ARN for status polling
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        staging_bucket_name: str,
        **kwargs
    ) -> None:
        """
        Initialize the Evaluation Job stack.

        Args:
            scope: CDK scope
            construct_id: Stack ID
            staging_bucket_name: Name of S3 bucket with evaluation data
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.staging_bucket_name = staging_bucket_name
        region = self.region
        account = self.account

        # =====================================================================
        # IAM Role for Bedrock Evaluation Jobs
        # =====================================================================

        # This role is assumed by Bedrock when running evaluation jobs
        evaluation_job_role = self._create_evaluation_job_role()

        # =====================================================================
        # Lambda Function (inline code - no external dependencies)
        # =====================================================================

        # Build Docker image from create_evaluation_job directory
        lambda_dir = Path(__file__).parent.parent / "lambda" / "create_evaluation_job"

        # Use inline code since only boto3 is needed (available in Lambda runtime)
        create_eval_lambda = lambda_.Function(
            self,
            "CreateEvaluationJobLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(str(lambda_dir)),
            timeout=Duration.seconds(60),  # 1 minute (API call is fast)
            memory_size=256,  # Minimal - just API calls
            environment={
                "STAGING_BUCKET": staging_bucket_name,
                "EVALUATION_ROLE_ARN": evaluation_job_role.role_arn,
                "JUDGE_MODEL_ID": "us.amazon.nova-pro-v1:0",  # Cost-effective for testing
                "MAX_EVALUATION_SAMPLES": "10",  # MVP limit for testing
            },
            description="Create Bedrock model evaluation jobs using filtered datasets",
        )

        # Grant Lambda permission to create evaluation jobs
        self._grant_lambda_permissions(create_eval_lambda)

        # CloudWatch Logs
        create_eval_lambda_logs = logs.LogGroup(
            self,
            "CreateEvalLambdaLogGroup",
            log_group_name=f"/aws/lambda/{create_eval_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # =====================================================================
        # Store references for other stacks
        # =====================================================================

        self.create_eval_lambda = create_eval_lambda
        self.evaluation_job_role = evaluation_job_role

        # =====================================================================
        # Stack Outputs
        # =====================================================================

        CfnOutput(
            self,
            "CreateEvalLambdaArn",
            value=create_eval_lambda.function_arn,
            description="ARN of the create_evaluation_job Lambda function",
            export_name=f"{self.stack_name}-CreateEvalLambdaArn",
        )

        CfnOutput(
            self,
            "CreateEvalLambdaName",
            value=create_eval_lambda.function_name,
            description="Name of the create_evaluation_job Lambda function",
            export_name=f"{self.stack_name}-CreateEvalLambdaName",
        )

        CfnOutput(
            self,
            "EvaluationJobRoleArn",
            value=evaluation_job_role.role_arn,
            description="ARN of the IAM role for Bedrock evaluation jobs",
            export_name=f"{self.stack_name}-EvaluationJobRoleArn",
        )

        CfnOutput(
            self,
            "TestCommand",
            value=(
                f"aws lambda invoke "
                f"--function-name {create_eval_lambda.function_name} "
                f'--payload \'{{"dataset_s3_uri":"s3://{staging_bucket_name}/evaluation-datasets/test/dataset.jsonl","question_count":5,"agent_name":"test-agent","metrics":["Builtin.Correctness"]}}\' '
                f"response.json && cat response.json | jq ."
            ),
            description="Command to test the create_evaluation_job Lambda directly",
        )

    def _create_evaluation_job_role(self) -> iam.Role:
        """
        Create IAM role for Bedrock evaluation jobs.

        This role is assumed by Bedrock when running evaluation jobs.
        It needs permissions to:
        - Read dataset from S3
        - Write results to S3
        - Invoke evaluator model (Nova Pro)
        """
        role = iam.Role(
            self,
            "EvaluationJobRole",
            role_name=f"EvaluationPipelineJobRole-{self.region}",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="IAM role for Bedrock model evaluation jobs",
        )

        # S3 permissions - read datasets and write results
        role.add_to_policy(
            iam.PolicyStatement(
                sid="S3BucketAccess",
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
                sid="S3ObjectAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                ],
                resources=[
                    f"arn:aws:s3:::{self.staging_bucket_name}/evaluation-datasets/*",
                    f"arn:aws:s3:::{self.staging_bucket_name}/evaluation-results/*",
                ],
            )
        )

        # Bedrock model access - for judge model (Nova Pro)
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockModelAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    # Nova Pro inference profile
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.nova-pro-v1:0",
                    f"arn:aws:bedrock:*::foundation-model/amazon.nova-pro*",
                    # Cross-region inference profile
                    f"arn:aws:bedrock:*:*:inference-profile/us.amazon.nova-pro-v1:0",
                ],
            )
        )

        return role

    def _grant_lambda_permissions(self, lambda_fn: lambda_.Function) -> None:
        """
        Grant Lambda permissions to create Bedrock evaluation jobs.

        Args:
            lambda_fn: Lambda function to grant permissions to
        """
        # Basic Lambda execution
        lambda_fn.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Bedrock CreateEvaluationJob permission
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockCreateEvaluationJob",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:CreateEvaluationJob",
                ],
                resources=["*"],  # CreateEvaluationJob doesn't support resource-level permissions
            )
        )

        # PassRole permission - allows Lambda to pass the evaluation role to Bedrock
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="PassRoleToBedrock",
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:PassRole",
                ],
                resources=[
                    f"arn:aws:iam::{self.account}:role/EvaluationPipelineJobRole-{self.region}",
                ],
                conditions={
                    "StringEquals": {
                        "iam:PassedToService": "bedrock.amazonaws.com"
                    }
                }
            )
        )
