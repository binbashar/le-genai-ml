#!/bin/bash

# Load Gateway M2M configuration from parent directory (if exists)
GATEWAY_DIR="../agentcore-gateway"
GATEWAY_OUTPUTS="$GATEWAY_DIR/gateway_outputs.json"
M2M_CONFIG="$GATEWAY_DIR/m2m_config.json"

# Check if Gateway configuration exists
if [ -f "$GATEWAY_OUTPUTS" ] && [ -f "$M2M_CONFIG" ]; then
    echo "🔗 Gateway configuration found - loading M2M credentials..."

    # Extract values using Python (more reliable than jq)
    GATEWAY_MCP_ENDPOINT=$(python3 -c "import json; print(json.load(open('$GATEWAY_OUTPUTS'))['gateway_endpoint'])" 2>/dev/null)
    GATEWAY_M2M_CLIENT_ID=$(python3 -c "import json; print(json.load(open('$M2M_CONFIG'))['client_id'])" 2>/dev/null)
    GATEWAY_M2M_CLIENT_SECRET=$(python3 -c "import json; print(json.load(open('$M2M_CONFIG'))['client_secret'])" 2>/dev/null)
    GATEWAY_TOKEN_ENDPOINT=$(python3 -c "import json; print(json.load(open('$M2M_CONFIG'))['token_endpoint'])" 2>/dev/null)
    GATEWAY_SCOPE=$(python3 -c "import json; print(json.load(open('$M2M_CONFIG')).get('scope', ''))" 2>/dev/null)

    # Build env args
    ENV_ARGS=(
        --env "GATEWAY_MCP_ENDPOINT=$GATEWAY_MCP_ENDPOINT"
        --env "GATEWAY_M2M_CLIENT_ID=$GATEWAY_M2M_CLIENT_ID"
        --env "GATEWAY_M2M_CLIENT_SECRET=$GATEWAY_M2M_CLIENT_SECRET"
        --env "GATEWAY_TOKEN_ENDPOINT=$GATEWAY_TOKEN_ENDPOINT"
    )

    # Add scope if exists
    if [ -n "$GATEWAY_SCOPE" ]; then
        ENV_ARGS+=(--env "GATEWAY_SCOPE=$GATEWAY_SCOPE")
    fi

    echo "   ✓ Gateway endpoint: ${GATEWAY_MCP_ENDPOINT:0:50}..."
    echo "   ✓ M2M Client ID: ${GATEWAY_M2M_CLIENT_ID:0:8}..."
    echo ""

    # Launch with Gateway environment variables
    uv run agentcore launch "${ENV_ARGS[@]}" "$@"
else
    echo "ℹ️  No Gateway configuration found - deploying without Gateway tools"
    echo ""

    # Launch without Gateway configuration
    uv run agentcore launch "$@"
fi
