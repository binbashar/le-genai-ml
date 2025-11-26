#!/usr/bin/env python3
"""
Evaluation Pipeline CDK Application

This CDK application deploys the infrastructure for collecting, transforming,
and querying Bedrock agent invocation logs for evaluation purposes.

Phase 1: CloudWatch → S3 bypass (no transformation) - COMPLETE
Phase 2: Lambda transformation with PII scrubbing - COMPLETE
Phase 4a: Filter Lambda (gather data) - COMPLETE
Phase 4b: Evaluation Job Lambda - COMPLETE
Phase 5: Step Functions Integration - CURRENT
"""

import os
import aws_cdk as cdk
from stacks.data_collection_stack import DataCollectionStack
from stacks.filter_lambda_stack import FilterLambdaStack
from stacks.evaluation_job_stack import EvaluationJobStack
from stacks.orchestration_stack import OrchestrationStack


app = cdk.App()

# Get environment configuration
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "us-west-2")
env = cdk.Environment(account=account, region=region)

# Feature flag: Enable Lambda transformation (Phase 2)
enable_transformation = app.node.try_get_context("enable_transformation")
if enable_transformation is None:
    enable_transformation = True  # Default: enabled for Phase 2

# Deploy data collection pipeline stack (Phase 1-2)
pipeline = DataCollectionStack(
    app,
    "EvaluationPipeline",
    enable_transformation=enable_transformation,
    env=env,
    description=f"Evaluation Pipeline - {'With Transformation' if enable_transformation else 'Bypass Mode'}",
)

# Feature flag: Deploy filter Lambda (Phase 4a)
deploy_filter_lambda = app.node.try_get_context("deploy_filter_lambda")
if deploy_filter_lambda is None:
    deploy_filter_lambda = False  # Default: disabled

# Deploy filter Lambda stack (Phase 4a)
filter_lambda_stack = None
if deploy_filter_lambda:
    filter_lambda_stack = FilterLambdaStack(
        app,
        "EvaluationPipelineFilterLambda",
        staging_bucket_name=pipeline.bucket_name,
        env=env,
        description="Filter Lambda - Read staging Parquet and create evaluation JSONL",
    )
    filter_lambda_stack.add_dependency(pipeline)

# Feature flag: Deploy evaluation job Lambda (Phase 4b)
deploy_evaluation_job = app.node.try_get_context("deploy_evaluation_job")
if deploy_evaluation_job is None:
    deploy_evaluation_job = False  # Default: disabled

# Deploy evaluation job Lambda stack (Phase 4b)
evaluation_job_stack = None
if deploy_evaluation_job:
    evaluation_job_stack = EvaluationJobStack(
        app,
        "EvaluationPipelineEvaluationJob",
        staging_bucket_name=pipeline.bucket_name,
        env=env,
        description="Evaluation Job Lambda - Create Bedrock model evaluation jobs",
    )
    evaluation_job_stack.add_dependency(pipeline)

# Feature flag: Deploy unified orchestration (Phase 5)
deploy_orchestration = app.node.try_get_context("deploy_orchestration")
if deploy_orchestration is None:
    deploy_orchestration = False  # Default: disabled

# Deploy orchestration stack (Phase 5 - requires filter + eval job stacks)
if deploy_orchestration:
    if not filter_lambda_stack or not evaluation_job_stack:
        raise ValueError(
            "Orchestration stack requires deploy_filter_lambda=true and deploy_evaluation_job=true"
        )

    orchestration = OrchestrationStack(
        app,
        "EvaluationPipelineOrchestration",
        filter_lambda_arn=filter_lambda_stack.filter_lambda.function_arn,
        create_eval_lambda_arn=evaluation_job_stack.create_eval_lambda.function_arn,
        staging_bucket_name=pipeline.bucket_name,
        env=env,
        description="Orchestration - Step Functions workflow for evaluation pipeline",
    )
    orchestration.add_dependency(filter_lambda_stack)
    orchestration.add_dependency(evaluation_job_stack)

cdk.Tags.of(app).add("Project", "genai-agentcore-demos")
cdk.Tags.of(app).add("Component", "evaluation-pipeline")
cdk.Tags.of(app).add("Phase", "5-orchestration")

app.synth()
