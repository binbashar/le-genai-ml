#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "🚀 Deploying Shared Cognito User Pool for AgentCore Demos"
echo ""

# Check if demo users file exists
if [ ! -f .demo_users.json ]; then
    echo "⚠️  Warning: .demo_users.json not found"
    echo "   The pool will be created without demo users."
    echo "   Copy .demo_users.json.example to .demo_users.json to add demo users."
    echo ""
fi

# Deploy CDK stack
echo "📦 Synthesizing CDK stack..."
uv run cdk synth

echo ""
echo "🚀 Deploying stack..."
uv run cdk deploy --require-approval never --outputs-file outputs.json

echo ""
echo "🔐 Running post-deployment setup..."
uv run python post_deploy.py

echo ""
echo "✅ Shared Cognito User Pool deployed successfully!"
echo ""
echo "📍 SSM Parameter: /agentcore/shared/cognito-pool-id"
echo ""
echo "Next steps:"
echo "1. Deploy agents: cd ../../finance-personal-assistant/cdk && ./deploy.sh"
echo "2. Deploy agents: cd ../../market-trends-agent/cdk && ./deploy.sh"
echo ""
