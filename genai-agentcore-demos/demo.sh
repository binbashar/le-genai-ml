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
#   - AWS credentials configured (AWS_PROFILE=binbash)
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

export AWS_PROFILE=binbash
cd ./ui && ./demo.sh "$@"
