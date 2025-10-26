#!/usr/bin/env python3
"""Sync agent config from deployments to Streamlit"""
from pathlib import Path

import yaml

# Agent directories
AGENTS = [
    "finance-personal-assistant",
    "market-trends-agent",
]


def dir_to_key(dir_name: str) -> str:
    """Convert directory name to agent key (hyphens to underscores)"""
    return dir_name.replace("-", "_")


def format_name(key: str) -> str:
    """Convert agent key to display name"""
    return key.replace("_", " ").title()


def get_agent_config(agent_dir: Path) -> dict | None:
    """Extract agent ARN and OAuth config from .bedrock_agentcore.yaml"""
    config_file = agent_dir / ".bedrock_agentcore.yaml"
    if not config_file.exists():
        return None

    with open(config_file) as f:
        config = yaml.safe_load(f)

    agents = config.get("agents", {})
    if not agents:
        return None

    # Prefer agent entry with OAuth config, fallback to first with ARN
    agent_data = None
    oauth_config = None

    for agent in agents.values():
        arn = agent.get("bedrock_agentcore", {}).get("agent_arn")
        if not arn:
            continue

        # Check for OAuth config
        auth_config = agent.get("authorizer_configuration") or {}
        jwt_auth = auth_config.get("customJWTAuthorizer")

        if jwt_auth:
            discovery_url = jwt_auth.get("discoveryUrl")
            allowed_clients = jwt_auth.get("allowedClients", [])

            if discovery_url and allowed_clients:
                # Found agent with OAuth - use this one
                agent_data = agent
                oauth_config = {
                    "discovery_url": discovery_url,
                    "client_id": allowed_clients[0],
                    "allowed_clients": allowed_clients,
                }
                break

        # No OAuth, but valid ARN - keep as fallback
        if not agent_data:
            agent_data = agent

    if not agent_data:
        return None

    arn = agent_data.get("bedrock_agentcore", {}).get("agent_arn")
    return {"arn": arn, "oauth_config": oauth_config}


def main():
    root = Path(__file__).parent
    agents_yaml = root / "streamlit-demo/config/agents.yaml"

    with open(agents_yaml) as f:
        config = yaml.safe_load(f)

    # Clear agents section - start fresh each sync
    config["agents"] = {}

    for agent_dir_name in AGENTS:
        agent_dir = root / agent_dir_name
        key = dir_to_key(agent_dir_name)
        agent_config = get_agent_config(agent_dir)

        if agent_config:
            config["agents"][key] = {
                "name": format_name(key),
                "arn": agent_config["arn"],
                "oauth_config": agent_config["oauth_config"],
            }
            auth_mode = "oauth" if agent_config["oauth_config"] else "iam"
            print(f"✓ {key}: {agent_config['arn'].split('/')[-1]} ({auth_mode})")
        else:
            print(f"⚠ {key}: not deployed, skipping")

    with open(agents_yaml, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    main()
