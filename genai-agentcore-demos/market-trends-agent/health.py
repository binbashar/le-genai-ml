#!/usr/bin/env python3
"""
Health check for Market Trends Agent

Default behavior: Cascading fallback (AWS → Local)
Tries each mode until one succeeds. Exit 0 if any mode works, exit 1 if all fail.

Modes:
  - AWS: Test deployed agent via AgentCore Runtime
  - Local: Test via local HTTP endpoint (localhost:8080)

Flags:
  --aws              Force AWS mode only
  --local            Force local mode only (requires: agentcore launch --local)
  --timeout SECONDS  Response timeout (default: 60)

Examples:
  # Cascading (default)
  ./health.sh
  uv run health.py

  # Force specific environment
  uv run health.py --aws
  uv run health.py --local

  # Adjust timeout
  uv run health.py --timeout 120
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.agentcore_health import AgentHealthConfig, create_health_check_cli  # type: ignore
from config import get_client


if __name__ == "__main__":
    config = AgentHealthConfig(
        agent_name="Market Trends Agent",
        agent_dir=str(Path(__file__).parent),
        arn_file=".agent_arn",
        default_prompt="Hello, are you operational?",
        aws_profile="binbash",
    )

    create_health_check_cli(config, get_client_func=get_client)
