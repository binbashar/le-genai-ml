#!/bin/bash
#
# Reset Runtime Memory for AgentCore Agents
#
# Clears runtime-created memories (LTM, runtime STM) while preserving
# configured STM memory infrastructure defined in .bedrock_agentcore.yaml.
#
# Usage:
#   ./reset_memory.sh --agent AGENT_NAME
#   ./reset_memory.sh --agent finance-personal-assistant
#
# Prerequisites:
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - Agent deployed with AgentCore Memory
#   - Python dependencies installed (uv sync from project root)
#
# What gets deleted:
#   - Runtime-created LTM memories (e.g., "FinancePersonalAssistantMemory-*")
#   - Additional STM created at runtime (different from configured STM)
#
# What gets preserved:
#   - Configured STM memory from .bedrock_agentcore.yaml (agent infrastructure)
#   - Memory configuration in SSM Parameter Store
#
# Use cases:
#   - Testing agent with clean memory state
#   - Removing stale/incorrect memories from development
#   - Preparing agent for demo/workshop (fresh start)
#
# WARNING: This operation cannot be undone. Deleted memories are permanent.
#
set -euo pipefail

cd "$(dirname "$0")"
export AWS_PROFILE="${AWS_PROFILE:-binbash}"

exec uv run python reset_memory.py "$@"
