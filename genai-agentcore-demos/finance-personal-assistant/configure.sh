#!/bin/bash
set -e

AGENT_NAME="finance_personal_assistant"
ENTRYPOINT="main.py"

echo "🔍 Reading configuration from SSM Parameter Store..."

# Try to get execution role ARN from SSM Parameter Store
EXECUTION_ROLE_ARN=$(aws ssm get-parameter \
    --name "/agentcore/${AGENT_NAME}/execution-role-arn" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

# Try to get OAuth config from SSM Parameter Store
OAUTH_CONFIG=$(aws ssm get-parameter \
    --name "/agentcore/${AGENT_NAME}/oauth-config" \
    --query "Parameter.Value" \
    --output text 2>/dev/null || echo "")

# Build agentcore configure command arguments as array
ARGS=("configure" "-e" "${ENTRYPOINT}" "-n" "${AGENT_NAME}" "--non-interactive")

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
