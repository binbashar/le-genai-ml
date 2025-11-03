#!/bin/bash
set -e

AGENT_NAME="finance_personal_assistant"

echo "🚀 Deploying agent to AWS Bedrock AgentCore Runtime..."
echo ""
echo "ℹ️  Gateway configuration auto-discovered via SSM Parameter Store at runtime"
echo "   (see utils/gateway.py for SSM-based config loading)"
echo ""

# Launch agent (Gateway config loaded from SSM at runtime via utils/gateway.py)
# Always use --auto-update-on-conflict to update existing agents with new configuration
uv run agentcore launch --auto-update-on-conflict "$@"

echo ""
echo "📝 Publishing agent configuration to SSM Parameter Store..."
uv run python ../shared/post_agent_deploy.py "$AGENT_NAME" .

echo ""
echo "✅ Deployment complete! Agent is now discoverable via SSM."
