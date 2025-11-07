#!/bin/bash
#
# Finance Personal Assistant - Deploy CDK Infrastructure
#
# Deploys Cognito User Pool, App Client, and IAM execution role using AWS CDK.
# Publishes OAuth configuration to SSM Parameter Store for automatic discovery.
#
# Usage:
#   ./deploy.sh
#
# Prerequisites:
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - AWS CDK CLI installed (npm install -g aws-cdk)
#   - Dependencies installed (uv sync from production directory)
#   - Optional: .demo_users.json file for automatic user creation
#
# What this script does:
#   1. Checks for demo users file (../../../.demo_users.json)
#      - If not found, automatically copies from .demo_users.json.example
#   2. Exports CDK environment variables (account, region)
#   3. Bootstraps CDK if needed (idempotent, one-time per account/region)
#   4. Deploys CloudFormation stack with Cognito + IAM resources
#   5. Saves stack outputs to outputs.json
#   6. Creates SSM parameters:
#      - /agentcore/finance_personal_assistant/config (OAuth configuration)
#      - /agentcore/finance_personal_assistant/execution-role-arn (IAM role)
#      - /agentcore/shared/cognito-pool-id (shared Cognito Pool)
#
# Demo users:
#   - File location: ../../../.demo_users.json (genai-agentcore-demos root)
#   - Automatically copied from .demo_users.json.example if not present
#   - Customize usernames, passwords, emails before deployment (optional)
#   - Users created automatically during deployment
#   - Format: JSON array with username, password, email, name fields
#
# Infrastructure created:
#   - Cognito User Pool (standard security config)
#   - Cognito App Client (OAuth2 ROPC flow)
#   - IAM execution role (comprehensive AgentCore permissions)
#   - SSM parameters (service discovery configuration)
#
# After deployment:
#   - Run ../configure.sh to read OAuth config and configure agent
#   - Run ../launch.sh to deploy agent to AgentCore Runtime
#   - OAuth config automatically discovered by Streamlit UI
#
set -e

echo "🚀 Deploying infrastructure..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .demo_users.json exists, if not copy from example
# Files are at genai-agentcore-demos root (3 levels up from cdk/)
DEMO_USERS_FILE="$SCRIPT_DIR/../../../.demo_users.json"
DEMO_USERS_EXAMPLE="$SCRIPT_DIR/../../../.demo_users.json.example"

if [ ! -f "$DEMO_USERS_FILE" ]; then
    if [ -f "$DEMO_USERS_EXAMPLE" ]; then
        echo "📋 Creating demo users file from example..."
        cp "$DEMO_USERS_EXAMPLE" "$DEMO_USERS_FILE"
        echo "✅ Demo users file created at $DEMO_USERS_FILE"
        echo "   You can edit this file to customize demo users"
    else
        echo "⚠️  Warning: $DEMO_USERS_FILE not found and no example file exists"
        echo "   Demo users will not be created"
    fi
else
    echo "✅ Using existing demo users file: $DEMO_USERS_FILE"
fi

# Export CDK environment variables for account and region resolution
# Assumes AWS_PROFILE is already set and user has run 'aws sso login' if needed
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region || echo "us-west-2")

echo "📍 Using AWS Account: ${CDK_DEFAULT_ACCOUNT}"
echo "📍 Using AWS Region: ${CDK_DEFAULT_REGION}"

# Bootstrap CDK if needed (only runs if not already bootstrapped)
echo "🔧 Checking CDK bootstrap status..."
uv run cdk bootstrap 2>/dev/null || true

# Deploy all CDK stacks and save outputs to outputs.json
echo "📦 Deploying CDK stacks..."
uv run cdk deploy --all \
    --outputs-file outputs.json \
    --require-approval never

# Check if deployment was successful
if [ ! -f "outputs.json" ]; then
    echo "❌ Error: outputs.json was not created. CDK deployment may have failed."
    exit 1
fi

echo ""
echo "✅ CDK deployment complete!"
echo ""
echo "🎉 OAuth infrastructure deployed!"
