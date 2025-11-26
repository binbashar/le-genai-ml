#!/bin/bash
#
# Deploy Evaluation Pipeline CDK Stack
#
# Usage:
#   ./deploy.sh                    # Deploy with transformation enabled (Phase 2)
#   ./deploy.sh --no-transform     # Deploy in bypass mode (Phase 1)
#

set -e

# Configuration
export AWS_PROFILE=binbash
export CDK_DEFAULT_ACCOUNT=905418344519
export CDK_DEFAULT_REGION=us-west-2

# Parse arguments
ENABLE_TRANSFORMATION=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-transform)
            ENABLE_TRANSFORMATION=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./deploy.sh [--no-transform]"
            exit 1
            ;;
    esac
done

echo "=================================================="
echo "Deploying Evaluation Pipeline"
echo "=================================================="
echo "AWS Profile: $AWS_PROFILE"
echo "Account: $CDK_DEFAULT_ACCOUNT"
echo "Region: $CDK_DEFAULT_REGION"
echo "Transformation: $ENABLE_TRANSFORMATION"
echo ""

# Synthesize CDK stack
echo "Step 1: Synthesizing CDK stack..."
if [ "$ENABLE_TRANSFORMATION" = "true" ]; then
    uv run cdk synth
else
    uv run cdk synth -c enable_transformation=false
fi

# Deploy stack
echo ""
echo "Step 2: Deploying stack..."
if [ "$ENABLE_TRANSFORMATION" = "true" ]; then
    uv run cdk deploy --require-approval never
else
    uv run cdk deploy --require-approval never -c enable_transformation=false
fi

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Configure Bedrock logging (run the ManualConfigCommand from stack outputs)"
echo "2. Invoke a Bedrock agent to generate logs"
echo "3. Check CloudWatch Logs: /aws/lambda/evaluation-pipeline-transform-bedrock-logs"
echo "4. Check S3 bucket for transformed data: eval-pipeline-$CDK_DEFAULT_ACCOUNT-$CDK_DEFAULT_REGION"
echo ""
