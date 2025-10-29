#!/bin/bash
# Reset runtime memory for AgentCore agents (preserves configured STM memory)
set -euo pipefail

cd "$(dirname "$0")"
export AWS_PROFILE="${AWS_PROFILE:-binbash}"

exec uv run python reset_memory.py "$@"
