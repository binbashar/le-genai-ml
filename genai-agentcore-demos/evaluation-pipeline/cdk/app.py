#!/usr/bin/env python3
"""
Evaluation Pipeline CDK Application

Deploys the complete evaluation pipeline infrastructure:
- Data Collection: CloudWatch → Firehose → Lambda → S3 Parquet
- Filter Lambda: Parquet → JSONL for Bedrock evaluation
- Evaluation Job Lambda: Create Bedrock evaluation jobs
- Orchestration: Step Functions workflow

Deployment:
    cd cdk
    AWS_PROFILE=binbash uv run cdk deploy EvaluationPipeline --require-approval never

    # After deployment, configure Bedrock logging (one-time):
    # Run the command from ManualConfigCommand output
"""

import os
import aws_cdk as cdk
from stacks.evaluation_pipeline_stack import EvaluationPipelineStack


app = cdk.App()

# Get environment configuration
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "us-west-2")
env = cdk.Environment(account=account, region=region)

# Optional: disable orchestration for testing base pipeline only
deploy_orchestration = app.node.try_get_context("deploy_orchestration")
if deploy_orchestration is None:
    deploy_orchestration = True  # Default: deploy everything

# Optional: disable guardrails for regex-only PII filtering
deploy_guardrails = app.node.try_get_context("deploy_guardrails")
if deploy_guardrails is None:
    deploy_guardrails = True  # Default: deploy Bedrock Guardrails for ML-based PII filtering

# Deploy unified evaluation pipeline stack
EvaluationPipelineStack(
    app,
    "EvaluationPipeline",
    deploy_orchestration=deploy_orchestration,
    deploy_guardrails=deploy_guardrails,
    env=env,
    description="Evaluation Pipeline - Unified infrastructure for agent evaluation",
)

cdk.Tags.of(app).add("Project", "genai-agentcore-demos")
cdk.Tags.of(app).add("Component", "evaluation-pipeline")

app.synth()
