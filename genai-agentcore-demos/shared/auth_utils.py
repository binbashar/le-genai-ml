"""
Generic Authentication Utilities
Provider-agnostic utilities for authentication and agent invocation
Supports: Cognito, OAuth2, API Keys, etc.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import boto3
import requests

logger = logging.getLogger(__name__)


def load_auth_config(config_file: Path) -> Optional[dict]:
    """
    Load authentication configuration from file

    Args:
        config_file: Path to .auth_config file

    Returns:
        dict with auth configuration or None if file doesn't exist

    Example config:
        {
            "provider": "cognito",
            "user_pool_id": "us-west-2_XXXXX",
            "client_id": "abc123...",
            "discovery_url": "https://..."
        }
    """
    if not config_file.exists():
        logger.debug(f"Auth config not found: {config_file}")
        return None

    try:
        with open(config_file) as f:
            config = json.load(f)
            logger.debug(f"Loaded auth config from: {config_file}")
            return config
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error loading auth config {config_file}: {e}")
        return None


def authenticate(provider_config: dict, username: str, password: str) -> dict:
    """
    Authenticate user with configured identity provider

    Args:
        provider_config: Auth configuration dict from load_auth_config()
        username: User's username
        password: User's password

    Returns:
        dict with authentication result (provider-specific)

    Raises:
        ValueError: If provider is unsupported or authentication fails
    """
    provider = provider_config.get("provider")

    if provider == "cognito":
        return _authenticate_cognito(provider_config, username, password)
    else:
        raise ValueError(
            f"Unsupported authentication provider: {provider}. "
            f"Supported providers: cognito"
        )


def _authenticate_cognito(config: dict, username: str, password: str) -> dict:
    """
    Authenticate user with Amazon Cognito

    Args:
        config: Cognito configuration with user_pool_id, client_id
        username: Cognito username
        password: User password

    Returns:
        dict with AuthenticationResult containing AccessToken, etc.

    Raises:
        ValueError: If authentication fails
    """
    try:
        # Extract region from user_pool_id (format: region_XXXXXX)
        user_pool_id = config["user_pool_id"]
        region = user_pool_id.split("_")[0]  # e.g., "us-west-2"

        cognito_client = boto3.client("cognito-idp", region_name=region)

        response = cognito_client.initiate_auth(
            ClientId=config["client_id"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )

        return response["AuthenticationResult"]

    except cognito_client.exceptions.NotAuthorizedException:
        raise ValueError("Invalid username or password")
    except cognito_client.exceptions.UserNotFoundException:
        raise ValueError("User not found")
    except KeyError as e:
        raise ValueError(f"Missing required config field: {e}")
    except Exception as e:
        logger.error(f"Cognito authentication error: {e}")
        raise ValueError(f"Authentication failed: {e}")


def invoke_with_token(
    agent_arn: str,
    token: str,
    prompt: str,
    session_id: str,
    region: str,
    timeout: int = 120,
) -> requests.Response:
    """
    Invoke AgentCore Runtime with bearer token (generic HTTP invocation)

    Args:
        agent_arn: Agent runtime ARN
        token: Bearer token (e.g., JWT from Cognito)
        prompt: User prompt
        session_id: Session ID for conversation context
        region: AWS region
        timeout: Request timeout in seconds

    Returns:
        Response object with streaming capability

    Raises:
        requests.HTTPError: If invocation fails
    """
    import urllib.parse

    # URL-encode the ARN
    arn_encoded = urllib.parse.quote(agent_arn, safe="")

    # Construct endpoint URL
    url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{arn_encoded}/invocations"

    # Headers with bearer token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    }

    # Query parameters
    params = {"qualifier": "DEFAULT"}

    # Request payload
    payload = {
        "prompt": prompt,
        "session_id": session_id,
    }

    logger.info(f"Invoking agent via HTTP: {url}")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Payload: {payload}")

    # Make HTTP POST request with streaming
    response = requests.post(
        url,
        headers=headers,
        params=params,
        json=payload,
        stream=True,
        timeout=timeout,
    )

    # Raise for HTTP errors
    response.raise_for_status()

    return response


def configure_agent_auth(
    agentcore_client,
    runtime_arn: str,
    auth_config: dict,
) -> None:
    """
    Configure authentication for AgentCore Runtime

    Args:
        agentcore_client: boto3 bedrock-agentcore-control client
        runtime_arn: Agent runtime ARN
        auth_config: Auth configuration dict

    Raises:
        ValueError: If provider is unsupported
    """
    provider = auth_config.get("provider")

    if provider == "cognito":
        # Extract runtime ID from ARN (format: arn:aws:bedrock-agentcore:region:account:runtime/runtime-id)
        runtime_id = runtime_arn.split("/")[-1]

        # First, get current runtime configuration (required for update)
        logger.info("   Retrieving current runtime configuration...")
        runtime_info = agentcore_client.get_agent_runtime(agentRuntimeId=runtime_id)

        # Update with authentication configuration
        agentcore_client.update_agent_runtime(
            agentRuntimeId=runtime_id,
            agentRuntimeArtifact=runtime_info["agentRuntimeArtifact"],
            roleArn=runtime_info["roleArn"],
            networkConfiguration=runtime_info["networkConfiguration"],
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": auth_config["discovery_url"],
                    "allowedClients": [auth_config["client_id"]],
                }
            },
        )
        logger.info(f"✅ Configured {provider} authentication for agent")
        logger.info(f"   Discovery URL: {auth_config['discovery_url']}")
        logger.info(f"   Client ID: {auth_config['client_id']}")

    else:
        raise ValueError(f"Unsupported provider for agent config: {provider}")


def get_auth_mode(config_file: Path) -> str:
    """
    Get authentication mode for an agent

    Args:
        config_file: Path to .auth_config file

    Returns:
        "iam" if no config or provider-specific mode (e.g., "cognito")
    """
    config = load_auth_config(config_file)
    if config:
        return config.get("provider", "iam")
    return "iam"
