#!/bin/bash
set -e

AGENT_NAME="finance_personal_assistant"

echo "🚀 Deploying agent to AWS Bedrock AgentCore Runtime..."
echo ""

# Launch agent - Always use --auto-update-on-conflict to update existing agents
uv run agentcore launch --auto-update-on-conflict "$@"

echo ""
echo "📝 Publishing agent configuration to SSM Parameter Store..."
uv run python ../libs/python/post_agent_deploy.py "$AGENT_NAME" .

echo ""
echo "✅ Deployment complete! Agent is now discoverable via SSM."
