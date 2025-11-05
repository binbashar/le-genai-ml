#!/bin/bash
set -e

echo "🚀 Deploying infrastructure..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .demo_users.json exists
DEMO_USERS_FILE="$SCRIPT_DIR/../../.demo_users.json"
if [ ! -f "$DEMO_USERS_FILE" ]; then
    echo "⚠️  Warning: $DEMO_USERS_FILE not found"
    echo "   To create demo users, copy .demo_users.json.example to .demo_users.json"
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
