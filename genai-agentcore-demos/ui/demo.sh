#!/bin/bash
#
# Streamlit Demo - Launch UI
#
# Starts the Streamlit web interface for AgentCore demos.
# Automatically discovers deployed agents from SSM Parameter Store at runtime.
#
# Usage:
#   ./demo.sh          # Standard mode (AWS agents)
#   ./demo.sh --local  # Local mode (connects to local Docker endpoints on port 8080)
#
# Prerequisites:
#   - At least one agent deployed (finance-personal-assistant, etc.)
#   - AWS credentials configured (export AWS_PROFILE=your-profile-name) for AWS mode
#   - Dependencies installed (uv sync from ui directory)
#   - Python path configured (automatic via PYTHONPATH export)
#
# Features:
#   - SSM-based agent discovery (reads /agentcore/*/config parameters)
#   - Real-time SSE streaming with tool execution feedback
#   - OAuth2/Cognito authentication support (when configured)
#   - Vision analysis (upload receipts, invoices)
#   - Document upload (CSV/PDF processing)
#   - Session-based conversation history (saved to sessions/ directory)
#   - LaTeX escaping for financial text ($1,200 displays correctly)
#
# Local mode (--local flag):
#   - Connects to local HTTP endpoints instead of AWS
#   - Requires agents running locally: 'agentcore launch --local'
#   - Default port: 8080 (configurable in config/agents.yaml)
#

if [ "$1" = "--local" ]; then
    export AGENTCORE_LOCAL_MODE=1
fi

# No sync needed - Streamlit auto-discovers agent config from SSM Parameter Store
export PYTHONPATH="${PYTHONPATH}:$(dirname "$PWD")"
uv run streamlit run app.py
