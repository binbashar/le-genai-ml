#!/bin/bash
#
# Demo Launcher - AgentCore Demos Streamlit UI
#
# Launches the Streamlit web interface with AWS profile configuration.
# The UI auto-discovers deployed agents from SSM Parameter Store at runtime.
#
# Usage:
#   ./demo.sh              # Standard mode (AWS agents)
#   ./demo.sh --local      # Local mode (connects to local Docker endpoints)
#
# Prerequisites:
#   - At least one agent deployed (finance-personal-assistant, etc.)
#   - AWS credentials configured with your profile (export AWS_PROFILE=your-profile-name)
#   - Streamlit dependencies installed (cd ui && uv sync)
#
# The Streamlit UI features:
#   - SSM-based agent discovery (no manual sync required)
#   - Real-time SSE streaming with tool execution feedback
#   - OAuth2/Cognito authentication support
#   - Vision analysis (receipts, invoices)
#   - Document upload (CSV/PDF)
#   - Session-based conversation history
#

# Check if AWS_PROFILE is set, otherwise show helpful message
if [ -z "$AWS_PROFILE" ]; then
  echo "❌ Error: AWS_PROFILE environment variable is not set."
  echo ""
  echo "Please configure your AWS profile and export it:"
  echo "  export AWS_PROFILE=your-profile-name"
  echo ""
  echo "See PRE_WORKSHOP_CHECKLIST.md for detailed configuration instructions."
  exit 1
fi

echo "🚀 Launching Streamlit UI with AWS_PROFILE=$AWS_PROFILE"
cd ./ui && ./demo.sh "$@"
