"""
Gateway MCP client factory.

Provides patterns for creating authenticated MCP clients.
- Immutable configuration with dataclasses
- Protocol-based credential providers
- Auto-discovery from environment variables or local files
- Type-safe with full type hints

Usage:
    from utils.gateway import create_mcp_client

    # Simple: auto-discover config, use default M2M auth
    mcp_client = create_mcp_client()

    # Advanced: custom config or credential provider
    config = GatewayConfig(endpoint="...", client_id="...", ...)
    mcp_client = create_mcp_client(config=config)
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GatewayConfig:
    """
    Immutable Gateway configuration.

    Attributes:
        endpoint: Gateway MCP endpoint URL (e.g., https://.../mcp)
        client_id: M2M OAuth client ID
        client_secret: M2M OAuth client secret
        token_endpoint: Cognito OAuth token endpoint
        scope: Optional custom OAuth scope
    """

    endpoint: str
    client_id: str
    client_secret: str
    token_endpoint: str
    scope: Optional[str] = None


class CredentialProvider(Protocol):
    """
    Protocol for extensible authentication strategies.

    Implementations:
    - M2MCredentialProvider: OAuth Client Credentials flow (default)
    - CachedM2MProvider: Add token caching (future)
    - TokenVaultProvider: AWS Secrets Manager integration (future)
    """

    def get_token(self, config: GatewayConfig) -> str:
        """
        Acquire access token for Gateway authentication.

        Args:
            config: Gateway configuration with credentials

        Returns:
            Access token (JWT)

        Raises:
            Exception: If token acquisition fails
        """
        ...


class M2MCredentialProvider:
    """
    Default credential provider using OAuth Client Credentials flow.

    Implements AWS-recommended M2M authentication pattern where
    the agent obtains its own token (not the user's token).

    Reference:
        https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html
    """

    def get_token(self, config: GatewayConfig) -> str:
        """
        Obtain M2M access token from Cognito using Client Credentials flow.

        Args:
            config: Gateway configuration with M2M credentials

        Returns:
            Access token (JWT)

        Raises:
            requests.HTTPError: If token request fails
        """
        # Encode credentials for Basic authentication
        credentials = f"{config.client_id}:{config.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Request token via Client Credentials flow
        data = {"grant_type": "client_credentials"}
        if config.scope:
            data["scope"] = config.scope

        logger.debug(f"[GATEWAY] Requesting M2M token from {config.token_endpoint}")

        response = requests.post(
            config.token_endpoint,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}",
            },
            data=data,
            timeout=10,
        )

        response.raise_for_status()
        token_data = response.json()

        expires_in = token_data.get("expires_in", "N/A")
        logger.info(f"[GATEWAY] ✓ M2M access token obtained (expires in {expires_in}s)")

        return token_data["access_token"]


def load_config_from_ssm(gateway_name: str = "agentcore-gateway", region: str = None) -> Optional[GatewayConfig]:
    """
    Load Gateway configuration from SSM Parameter Store and Secrets Manager.

    This is the preferred method for CDK deployments.

    Args:
        gateway_name: Gateway name (default: agentcore-gateway)
        region: AWS region (defaults to boto3 session region)

    Returns:
        Gateway configuration or None if not found
    """
    try:
        import boto3

        session = boto3.Session(region_name=region) if region else boto3.Session()
        ssm = session.client('ssm')
        sm = session.client('secretsmanager')

        # Load Gateway config from SSM
        config_param = f"/agentcore/{gateway_name}/config"
        try:
            response = ssm.get_parameter(Name=config_param)
            gateway_config = json.loads(response['Parameter']['Value'])
        except ssm.exceptions.ParameterNotFound:
            logger.debug(f"[GATEWAY] SSM parameter not found: {config_param}")
            return None

        # Load M2M credentials from Secrets Manager
        secret_name = f"/agentcore/{gateway_name}/m2m-secret"
        try:
            secret_response = sm.get_secret_value(SecretId=secret_name)
            m2m_secret = json.loads(secret_response['SecretString'])
        except sm.exceptions.ResourceNotFoundException:
            logger.debug(f"[GATEWAY] Secret not found: {secret_name}")
            return None

        # Construct Gateway endpoint
        # Gateway config stores base endpoint without /mcp suffix
        endpoint = gateway_config.get("gateway_endpoint")
        if not endpoint.endswith("/mcp"):
            endpoint = f"{endpoint}/mcp"

        config = GatewayConfig(
            endpoint=endpoint,
            client_id=m2m_secret["client_id"],
            client_secret=m2m_secret["client_secret"],
            token_endpoint=m2m_secret["token_endpoint"],
            scope=m2m_secret.get("scope"),
        )

        logger.info("[GATEWAY] ✓ Configuration loaded from SSM + Secrets Manager")
        logger.info(f"[GATEWAY]   Endpoint: {config.endpoint}")
        logger.info(f"[GATEWAY]   M2M Client: {config.client_id[:8]}...")
        logger.info(f"[GATEWAY]   Token Endpoint: {config.token_endpoint}")

        return config

    except ImportError:
        logger.debug("[GATEWAY] boto3 not available - skipping SSM lookup")
        return None
    except Exception as e:
        logger.debug(f"[GATEWAY] Could not load from SSM: {e}")
        return None


def load_config_from_env() -> Optional[GatewayConfig]:
    """
    Load Gateway configuration from environment variables.

    Environment Variables:
        GATEWAY_MCP_ENDPOINT: Gateway MCP endpoint URL
        GATEWAY_M2M_CLIENT_ID: M2M OAuth client ID
        GATEWAY_M2M_CLIENT_SECRET: M2M OAuth client secret
        GATEWAY_TOKEN_ENDPOINT: Cognito token endpoint
        GATEWAY_SCOPE: Optional custom OAuth scope

    Returns:
        Gateway configuration or None if not configured
    """
    endpoint = os.environ.get("GATEWAY_MCP_ENDPOINT")
    client_id = os.environ.get("GATEWAY_M2M_CLIENT_ID")
    client_secret = os.environ.get("GATEWAY_M2M_CLIENT_SECRET")
    token_endpoint = os.environ.get("GATEWAY_TOKEN_ENDPOINT")
    scope = os.environ.get("GATEWAY_SCOPE")

    if all([endpoint, client_id, client_secret, token_endpoint]):
        logger.info("[GATEWAY] ✓ Configuration loaded from environment variables")
        logger.info(f"[GATEWAY]   Endpoint: {endpoint}")
        logger.info(f"[GATEWAY]   M2M Client: {client_id[:8]}...")
        logger.info(f"[GATEWAY]   Token Endpoint: {token_endpoint}")

        return GatewayConfig(
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=token_endpoint,
            scope=scope,
        )

    return None


# File-based configuration removed - use SSM Parameter Store or environment variables only
# This ensures production-grade configuration management and eliminates cross-directory dependencies


def load_config(gateway_name: str = "agentcore-gateway", region: str = None) -> Optional[GatewayConfig]:
    """
    Auto-discover Gateway configuration with cascading fallback.

    Priority:
    1. SSM Parameter Store + Secrets Manager (CDK deployment - PRODUCTION)
    2. Environment variables (Docker/local development)
    3. None (graceful degradation - agent uses embedded tools)

    Args:
        gateway_name: Gateway name for SSM lookup (default: agentcore-gateway)
        region: AWS region for SSM lookup (optional)

    Returns:
        Gateway configuration or None if not configured
    """
    # Priority 1: SSM Parameter Store (production)
    config = load_config_from_ssm(gateway_name=gateway_name, region=region)
    if config:
        return config

    # Priority 2: Environment variables (development)
    config = load_config_from_env()
    if config:
        return config

    # No configuration found - graceful degradation
    logger.debug("[GATEWAY] Gateway not configured - using embedded tools only")
    return None


def create_mcp_client(
    config: Optional[GatewayConfig] = None,
    credential_provider: Optional[CredentialProvider] = None,
    gateway_name: str = "agentcore-gateway",
    region: str = None,
):
    """
    Create authenticated MCP client for Gateway.

    This is the main entry point for Gateway integration. It handles:
    - Auto-discovery of configuration
    - Token acquisition via credential provider
    - MCP transport creation with Bearer authentication
    - Graceful degradation if Gateway not configured

    Args:
        config: Gateway configuration (auto-discovered if None)
        credential_provider: Auth strategy (M2M if None)
        gateway_name: Gateway name for SSM lookup (default: agentcore-gateway)
        region: AWS region for SSM lookup (optional)

    Returns:
        MCPClient instance or None if Gateway not configured

    Example:
        # Simple: auto-discover config, use default M2M auth
        mcp_client = create_mcp_client()

        # Advanced: custom credential provider
        provider = CachedM2MProvider()
        mcp_client = create_mcp_client(credential_provider=provider)

        # Custom gateway
        mcp_client = create_mcp_client(gateway_name="my-gateway", region="us-east-1")
    """
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from strands.tools.mcp.mcp_client import MCPClient
    except ImportError:
        logger.warning(
            "[GATEWAY] MCP libraries not available - install with: uv add mcp strands-agents-tools"
        )
        return None

    # Temporarily disable Gateway due to authentication issues
    # TODO: Re-enable when Gateway auth is fixed
    # When re-enabling:
    #   1. Uncomment code below (config discovery, M2M auth, MCP client creation)
    #   2. Test with: cd ../agentcore-gateway && uv run python scripts/test_m2m_auth.py
    #   3. Remove this early return
    logger.info("[GATEWAY] Gateway temporarily disabled - using embedded tools only")
    return None

    # UNREACHABLE CODE BELOW (commented out for clarity)
    # Restore when Gateway auth is fixed
    #
    # # Auto-discover config if not provided
    # config = config or load_config(gateway_name=gateway_name, region=region)
    # if not config:
    #     logger.debug("[GATEWAY] Gateway not configured - using embedded tools only")
    #     return None
    #
    # # Use default M2M provider if not specified
    # credential_provider = credential_provider or M2MCredentialProvider()
    #
    # try:
    #     logger.info("[GATEWAY] Initiating M2M authentication flow")
    #
    #     # Obtain access token
    #     access_token = credential_provider.get_token(config)
    #
    #     # Create MCP transport with Bearer token
    #     logger.info(f"[GATEWAY] Connecting to Gateway: {config.endpoint}")
    #
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Bearer {access_token}",
    #     }
    #
    #     transport = streamablehttp_client(config.endpoint, headers=headers)
    #
    #     # Create MCP client
    #     mcp_client = MCPClient(lambda: transport)
    #
    #     logger.info("[GATEWAY] ✓ MCP client initialized successfully")
    #     logger.info(f"[GATEWAY]   Endpoint: {config.endpoint}")
    #     logger.info("[GATEWAY]   Auth mode: M2M OAuth (Client Credentials)")
    #
    #     return mcp_client
    #
    # except Exception as e:
    #     logger.warning(f"[GATEWAY] ✗ Could not initialize MCP client: {e}")
    #     logger.info(
    #         "[GATEWAY] Agent will use embedded tools only (graceful degradation)"
    #     )
    #     return None
