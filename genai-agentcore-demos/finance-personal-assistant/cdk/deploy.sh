#!/bin/bash
set -e

echo "🚀 Deploying Cognito infrastructure for finance-personal-assistant..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .demo_users.json exists
DEMO_USERS_FILE="$SCRIPT_DIR/../../.demo_users.json"
if [ ! -f "$DEMO_USERS_FILE" ]; then
    echo "⚠️  Warning: $DEMO_USERS_FILE not found"
    echo "   To create demo users, copy .demo_users.json.example to .demo_users.json"
fi

# Set CDK profile flag if AWS_PROFILE is set
PROFILE_FLAG=""
if [ -n "${AWS_PROFILE}" ]; then
    PROFILE_FLAG="--profile ${AWS_PROFILE}"
fi

# Bootstrap CDK if needed (only runs if not already bootstrapped)
echo "🔧 Checking CDK bootstrap status..."
uv run cdk bootstrap ${PROFILE_FLAG} 2>/dev/null || true

# Deploy the CDK stack and save outputs to outputs.json
echo "📦 Deploying CDK stack..."
uv run cdk deploy \
    ${PROFILE_FLAG} \
    --outputs-file outputs.json \
    --require-approval never

# Check if deployment was successful
if [ ! -f "outputs.json" ]; then
    echo "❌ Error: outputs.json was not created. CDK deployment may have failed."
    exit 1
fi

echo "✅ CDK deployment complete!"

# Run post-deployment script to create .auth_config
echo "⚙️  Running post-deployment configuration..."
uv run python post_deploy.py

# Verify .auth_config was created
AUTH_CONFIG="$SCRIPT_DIR/../.auth_config"
if [ -f "$AUTH_CONFIG" ]; then
    echo "✅ Created $AUTH_CONFIG"
    echo ""
    echo "📄 Authentication configuration:"
    cat "$AUTH_CONFIG"
else
    echo "❌ Error: .auth_config was not created"
    exit 1
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Use the credentials from .demo_users.json to authenticate"
echo "   2. The .auth_config file is ready for health checks and Streamlit"
