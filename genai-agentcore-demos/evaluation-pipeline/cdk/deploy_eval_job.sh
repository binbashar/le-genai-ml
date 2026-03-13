#!/bin/bash
#
# Deploy Evaluation Job Lambda CDK Stack
#
# Usage:
#   ./deploy_eval_job.sh
#

set -e

# Configuration
export AWS_PROFILE=binbash
export CDK_DEFAULT_ACCOUNT=905418344519
export CDK_DEFAULT_REGION=us-west-2
export AWS_SDK_LOAD_CONFIG=1  # Ensure Python SDK loads config

echo "=================================================="
echo "Deploying Evaluation Job Lambda"
echo "=================================================="
echo "AWS Profile: $AWS_PROFILE"
echo "Account: $CDK_DEFAULT_ACCOUNT"
echo "Region: $CDK_DEFAULT_REGION"
echo ""

# Synthesize CDK stack
echo "Step 1: Synthesizing CDK stack..."
uv run cdk synth EvaluationPipelineEvaluationJob -c deploy_evaluation_job=true

# Deploy stack
echo ""
echo "Step 2: Deploying stack..."
uv run cdk deploy EvaluationPipelineEvaluationJob -c deploy_evaluation_job=true --require-approval never

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. View stack outputs: aws cloudformation describe-stacks --stack-name EvaluationPipelineEvaluationJob"
echo "2. Test Lambda function (check outputs for test command)"
echo "3. Check CloudWatch Logs for deployment confirmation"
echo ""
