#!/bin/bash
#
# Finance Personal Assistant - Configure Agent
#
# Reads configuration from SSM Parameter Store and creates .bedrock_agentcore.yaml
# for AgentCore Runtime deployment. Supports both OAuth2/Cognito and IAM authentication.
#
# Usage:
#   ./configure.sh
#
# Prerequisites:
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - Optional: CDK infrastructure deployed (./cdk/deploy.sh) for OAuth support
#   - Dependencies installed (uv sync)
#
# What this script does:
#   1. Reads execution role ARN from SSM (if exists)
#   2. Reads OAuth configuration from SSM (if exists)
#   3. Runs 'agentcore configure' to create .bedrock_agentcore.yaml
#   4. Configures entrypoint (main.py), memory (disabled), request headers
#   5. Adds OAuth authorizer config if found in SSM
#
# Authentication modes:
#   - OAuth/Cognito: If /agentcore/finance_personal_assistant/config contains OAuth config
#   - IAM: If no OAuth config in SSM (uses AWS credentials)
#
# SSM Parameters read:
#   - /agentcore/finance_personal_assistant/execution-role-arn (optional)
#   - /agentcore/finance_personal_assistant/config (optional, contains OAuth)
#
# Output:
#   - .bedrock_agentcore.yaml (ready for 'agentcore launch')
#
set -e

AGENT_NAME="finance_personal_assistant"
ENTRYPOINT="main.py"

echo "🔍 Reading configuration from SSM Parameter Store..."

# Try to get execution role ARN from SSM Parameter Store
EXECUTION_ROLE_ARN=$(aws ssm get-parameter \
    --name "/agentcore/${AGENT_NAME}/execution-role-arn" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

# Try to get unified config from SSM Parameter Store
UNIFIED_CONFIG=$(aws ssm get-parameter \
    --name "/agentcore/${AGENT_NAME}/config" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

# Extract OAuth config from unified config if exists
OAUTH_CONFIG=""
if [ -n "$UNIFIED_CONFIG" ]; then
    OAUTH_CONFIG=$(echo "$UNIFIED_CONFIG" | jq -c '.oauth // empty' 2>/dev/null || echo "")
fi

# Build agentcore configure command arguments as array
ARGS=("configure" "-e" "${ENTRYPOINT}" "-n" "${AGENT_NAME}" "--non-interactive")

# Add request header allowlist for OAuth authentication and custom user ID
echo "✅ Configuring request headers: Authorization, X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
ARGS+=("--request-header-allowlist" "Authorization,X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id")

echo "✅ Disabling auto-managed memory"
ARGS+=("--disable-memory")

if [ -n "$EXECUTION_ROLE_ARN" ]; then
    echo "✅ Found execution role ARN: ${EXECUTION_ROLE_ARN}"
    ARGS+=("--execution-role" "${EXECUTION_ROLE_ARN}")
else
    echo "ℹ️  No execution role ARN found in SSM, agentcore CLI will auto-create role"
fi

if [ -n "$OAUTH_CONFIG" ]; then
    echo "✅ Found OAuth configuration in SSM"
    ARGS+=("--authorizer-config" "${OAUTH_CONFIG}")
else
    echo "ℹ️  No OAuth configuration found, using IAM authentication"
fi

# Execute configure command with any additional arguments
echo ""
echo "📝 Configuring ${AGENT_NAME}..."
uv run agentcore "${ARGS[@]}" "$@"

echo ""
echo "✅ Configuration complete!"
