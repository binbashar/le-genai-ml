#!/bin/bash
#
# Finance Personal Assistant - Deploy Agent
#
# Builds Docker image, pushes to ECR, and deploys to AWS Bedrock AgentCore Runtime.
# Automatically publishes agent ARN to SSM Parameter Store for service discovery.
#
# Usage:
#   ./launch.sh
#
# Prerequisites:
#   - .bedrock_agentcore.yaml exists (created by ./configure.sh)
#   - Docker daemon running (for image build)
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - Dependencies installed (uv sync)
#
# What this script does:
#   1. Builds Docker container with agent code (automatic via 'agentcore launch')
#   2. Pushes image to ECR repository (auto-created if not exists)
#   3. Creates/updates AgentCore Runtime instance
#   4. Creates DEFAULT endpoint (points to latest version)
#   5. Publishes agent ARN to SSM: /agentcore/finance_personal_assistant/config
#
# Output:
#   - AgentCore Runtime with immutable version number
#   - ECR repository and Docker image
#   - SSM parameter updated with agent ARN (enables Streamlit UI discovery)
#
# Deployment features:
#   - Immutable versioning (new version on each deployment)
#   - --auto-update-on-conflict (updates existing agents)
#   - OpenTelemetry instrumentation (automatic observability)
#   - Non-root container user (security best practice)
#
# After deployment:
#   - Test with: ./health.sh
#   - View logs: aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
#   - Streamlit UI auto-discovers agent via SSM (no manual sync needed)
#
set -e

AGENT_NAME="finance_personal_assistant"

echo "🚀 Deploying agent to AWS Bedrock AgentCore Runtime..."
echo ""

# Launch agent - Always use --auto-update-on-conflict to update existing agents
uv run agentcore launch --auto-update-on-conflict "$@"

echo ""
echo "📝 Publishing agent configuration to SSM Parameter Store..."
uv run python ../../libs/python/post_agent_deploy.py "$AGENT_NAME" .

echo ""
echo "✅ Deployment complete! Agent is now discoverable via SSM."
