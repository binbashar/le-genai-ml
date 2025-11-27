#!/usr/bin/env python3
"""Health check for Browser Agent using shared health check module"""

import sys
from pathlib import Path

# Add parent directory to path for libs module access
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli

from config import get_client

if __name__ == "__main__":
    config = AgentHealthConfig(
        agent_name="browser_agent",
        agent_dir=str(Path(__file__).parent),
        default_prompt="Navigate to https://example.com and tell me what you see",
        aws_profile="binbash",
    )

    create_health_check_cli(config, get_client_func=get_client)
