#!/bin/bash
#
# Chat Agent - Deploy CDK Infrastructure
#
# Deploys named IAM execution role for agent identification in evaluation pipeline.
# The role name follows: BedrockAgentCore-chat_agent-execution-role
#
# Usage:
#   ./deploy.sh
#
# Prerequisites:
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - AWS CDK CLI installed (npm install -g aws-cdk)
#   - Dependencies installed (uv sync from chat-agent directory)
#
# What this script does:
#   1. Exports CDK environment variables (account, region)
#   2. Bootstraps CDK if needed (idempotent, one-time per account/region)
#   3. Deploys CloudFormation stack with IAM execution role
#   4. Saves stack outputs to outputs.json
#   5. Creates SSM parameter: /agentcore/chat_agent/execution-role-arn
#
# Infrastructure created:
#   - IAM execution role (BedrockAgentCore-chat_agent-execution-role)
#   - SSM parameter (execution role ARN for agent configuration)
#
# After deployment:
#   - Run ../configure.sh to configure agent with execution role
#   - Run ../launch.sh to deploy agent to AgentCore Runtime
#
set -e

echo "Deploying chat_agent infrastructure..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Export CDK environment variables for account and region resolution
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region || echo "us-west-2")

echo "Using AWS Account: ${CDK_DEFAULT_ACCOUNT}"
echo "Using AWS Region: ${CDK_DEFAULT_REGION}"

# Bootstrap CDK if needed (only runs if not already bootstrapped)
echo "Checking CDK bootstrap status..."
uv run cdk bootstrap 2>/dev/null || true

# Deploy all CDK stacks and save outputs to outputs.json
echo "Deploying CDK stacks..."
uv run cdk deploy --all \
    --outputs-file outputs.json \
    --require-approval never

# Check if deployment was successful
if [ ! -f "outputs.json" ]; then
    echo "Error: outputs.json was not created. CDK deployment may have failed."
    exit 1
fi

echo ""
echo "CDK deployment complete!"
echo "Execution role published to SSM: /agentcore/chat_agent/execution-role-arn"
echo ""
echo "Next steps:"
echo "  cd .. && ./configure.sh && ./launch.sh"
