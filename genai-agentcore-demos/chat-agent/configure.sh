#!/bin/bash
#
# Chat Agent - Configure Agent
#
# Creates .bedrock_agentcore.yaml for AgentCore Runtime deployment.
# Uses IAM authentication (no OAuth/Cognito setup required).
# Reads execution role ARN from SSM Parameter Store (created by CDK).
#
# Usage:
#   ./configure.sh
#
# Prerequisites:
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - Dependencies installed (uv sync)
#   - CDK infrastructure deployed (cd cdk && ./deploy.sh)
#
# What this script does:
#   1. Reads execution role ARN from SSM: /agentcore/chat_agent/execution-role-arn
#   2. Runs 'agentcore configure' to create .bedrock_agentcore.yaml
#   3. Configures entrypoint (main.py) with named execution role
#   4. Memory enabled by default (AgentCore-managed)
#   5. Adds request headers for custom user/session ID
#
# Output:
#   - .bedrock_agentcore.yaml (ready for 'agentcore launch')
#
set -e

AGENT_NAME="chat_agent"
ENTRYPOINT="main.py"

echo "Reading configuration from SSM Parameter Store..."

# Try to get execution role ARN from SSM Parameter Store
EXECUTION_ROLE_ARN=$(aws ssm get-parameter \
    --name "/agentcore/${AGENT_NAME}/execution-role-arn" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

# Build agentcore configure command
ARGS=("configure" "-e" "${ENTRYPOINT}" "-n" "${AGENT_NAME}" "--non-interactive")

# Use container deployment (builds dependencies in Docker - more compatible)
echo "Using container deployment mode"
ARGS+=("--deployment-type" "container")

# Add request header allowlist for custom user ID (Authorization only allowed with OAuth)
echo "Configuring request headers: X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
ARGS+=("--request-header-allowlist" "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id")

# Add execution role ARN if found in SSM
if [ -n "$EXECUTION_ROLE_ARN" ]; then
    echo "Found execution role ARN: ${EXECUTION_ROLE_ARN}"
    ARGS+=("--execution-role" "${EXECUTION_ROLE_ARN}")
else
    echo "WARNING: No execution role ARN found in SSM"
    echo "         Run: cd cdk && ./deploy.sh"
    echo "         Then re-run this script"
    echo ""
    echo "Proceeding without custom execution role (evaluation pipeline won't identify this agent)"
fi

# Memory is enabled by default (AgentCore will create and manage it)
echo "Memory enabled by default (AgentCore-managed)"

echo ""
echo "Using IAM authentication (no OAuth configuration)"
echo ""

# Execute configure command with any additional arguments
uv run agentcore "${ARGS[@]}" "$@"

echo ""
echo "Configuration complete!"
echo "   Next step: ./launch.sh"
