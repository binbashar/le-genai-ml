"""
SSM Parameter Store utilities for AgentCore configuration discovery.

Enables production-grade configuration management without file dependencies.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import boto3 (optional dependency)
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.debug("boto3 not available - SSM utilities disabled")


def get_agent_runtime_config(
    agent_name: str, region: str = "us-west-2"
) -> Optional[dict]:
    """
    Get agent runtime configuration from SSM Parameter Store.

    This enables Streamlit and other services to auto-discover agent config
    without manual sync scripts or file dependencies.

    Args:
        agent_name: Agent name (e.g., "finance_personal_assistant")
        region: AWS region (default: us-west-2)

    Returns:
        Runtime config dict:
        {
            "arn": "arn:aws:bedrock-agentcore:...",
            "oauth_config": {
                "discovery_url": "https://...",
                "client_id": "...",
                "allowed_clients": ["..."]
            } or None
        }
        Returns None if parameter not found.

    Example:
        >>> config = get_agent_runtime_config("finance_personal_assistant")
        >>> if config:
        ...     agent_arn = config["arn"]
        ...     oauth_config = config.get("oauth_config")
    """
    if not BOTO3_AVAILABLE:
        logger.debug("boto3 not available - cannot read SSM parameters")
        return None

    try:
        ssm = boto3.client("ssm", region_name=region)
        param_name = f"/agentcore/{agent_name}/config"

        response = ssm.get_parameter(Name=param_name)
        unified_config = json.loads(response["Parameter"]["Value"])

        # Transform unified config to expected format
        # Unified format: {"arn": "...", "oauth": {"customJWTAuthorizer": {...}}}
        # Expected format: {"arn": "...", "oauth_config": {"discovery_url": "...", ...}}

        runtime_config = {
            "arn": unified_config.get("arn"),
            "oauth_config": None,
        }

        # Extract and transform OAuth config if present
        oauth_section = unified_config.get("oauth", {})
        jwt_auth = oauth_section.get("customJWTAuthorizer")

        if jwt_auth:
            discovery_url = jwt_auth.get("discoveryUrl")
            allowed_clients = jwt_auth.get("allowedClients", [])

            if discovery_url and allowed_clients:
                runtime_config["oauth_config"] = {
                    "discovery_url": discovery_url,
                    "client_id": allowed_clients[0],
                    "allowed_clients": allowed_clients,
                }

        logger.debug(f"Loaded runtime config from SSM: {param_name}")
        return runtime_config

    except ssm.exceptions.ParameterNotFound:
        logger.debug(f"SSM parameter not found: /agentcore/{agent_name}/config")
        return None
    except Exception as e:
        logger.warning(f"Error reading agent runtime config from SSM: {e}")
        return None


def get_all_agent_configs(region: str = "us-west-2") -> dict[str, dict]:
    """
    Get runtime config for all deployed agents.

    Returns:
        Dict mapping agent names to their runtime configs:
        {
            "finance_personal_assistant": {"arn": "...", "oauth_config": {...}}
        }

    Example:
        >>> configs = get_all_agent_configs()
        >>> for agent_name, config in configs.items():
        ...     print(f"{agent_name}: {config['arn']}")
    """
    if not BOTO3_AVAILABLE:
        return {}

    try:
        ssm = boto3.client("ssm", region_name=region)

        # List all parameters under /agentcore/*/config
        response = ssm.get_parameters_by_path(
            Path="/agentcore",
            Recursive=True,
        )

        configs = {}
        for param in response["Parameters"]:
            # Extract agent name from path: /agentcore/{agent_name}/config
            param_name = param["Name"]
            if param_name.endswith("/config"):
                agent_name = param_name.split("/")[2]  # /agentcore/{agent_name}/config
                unified_config = json.loads(param["Value"])

                # Transform to expected format (same as get_agent_runtime_config)
                runtime_config = {
                    "arn": unified_config.get("arn"),
                    "oauth_config": None,
                }

                # Extract and transform OAuth config if present
                oauth_section = unified_config.get("oauth", {})
                jwt_auth = oauth_section.get("customJWTAuthorizer")

                if jwt_auth:
                    discovery_url = jwt_auth.get("discoveryUrl")
                    allowed_clients = jwt_auth.get("allowedClients", [])

                    if discovery_url and allowed_clients:
                        runtime_config["oauth_config"] = {
                            "discovery_url": discovery_url,
                            "client_id": allowed_clients[0],
                            "allowed_clients": allowed_clients,
                        }

                configs[agent_name] = runtime_config

        logger.debug(f"Loaded {len(configs)} agent configs from SSM")
        return configs

    except Exception as e:
        logger.warning(f"Error reading agent configs from SSM: {e}")
        return {}
