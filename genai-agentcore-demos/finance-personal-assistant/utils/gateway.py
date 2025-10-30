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


def load_config() -> Optional[GatewayConfig]:
    """
    Auto-discover Gateway configuration.

    Priority:
    1. Environment variables (production, Docker)
    2. Local files (development)
    3. None (graceful degradation)

    Environment Variables:
        GATEWAY_MCP_ENDPOINT: Gateway MCP endpoint URL
        GATEWAY_M2M_CLIENT_ID: M2M OAuth client ID
        GATEWAY_M2M_CLIENT_SECRET: M2M OAuth client secret
        GATEWAY_TOKEN_ENDPOINT: Cognito token endpoint
        GATEWAY_SCOPE: Optional custom OAuth scope

    Local Files (development):
        ../agentcore-gateway/gateway_outputs.json
        ../agentcore-gateway/m2m_config.json

    Returns:
        Gateway configuration or None if not configured
    """
    # Try environment variables first (production, Docker)
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

    # Fall back to local files (development)
    try:
        gateway_dir = Path(__file__).parent.parent.parent / "agentcore-gateway"
        outputs_file = gateway_dir / "gateway_outputs.json"

        if not outputs_file.exists():
            logger.debug("[GATEWAY] Gateway not configured (no env vars, no files)")
            return None

        with open(outputs_file) as f:
            outputs = json.load(f)

        if not outputs.get("cognito_configured"):
            logger.debug("[GATEWAY] Gateway OAuth not configured")
            return None

        m2m_config_file = gateway_dir / "m2m_config.json"
        if not m2m_config_file.exists():
            logger.warning("[GATEWAY] m2m_config.json not found")
            return None

        with open(m2m_config_file) as f:
            m2m_config = json.load(f)

        config = GatewayConfig(
            endpoint=outputs["gateway_endpoint"],
            client_id=m2m_config["client_id"],
            client_secret=m2m_config["client_secret"],
            token_endpoint=m2m_config["token_endpoint"],
            scope=m2m_config.get("scope"),
        )

        logger.info("[GATEWAY] ✓ Configuration loaded from files")
        logger.info(f"[GATEWAY]   Endpoint: {config.endpoint}")
        logger.info(f"[GATEWAY]   M2M Client: {config.client_id[:8]}...")
        logger.info(f"[GATEWAY]   Token Endpoint: {config.token_endpoint}")

        return config

    except Exception as e:
        logger.warning(f"[GATEWAY] Could not load configuration: {e}")
        return None


def create_mcp_client(
    config: Optional[GatewayConfig] = None,
    credential_provider: Optional[CredentialProvider] = None,
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

    Returns:
        MCPClient instance or None if Gateway not configured

    Example:
        # Simple: auto-discover config, use default M2M auth
        mcp_client = create_mcp_client()

        # Advanced: custom credential provider
        provider = CachedM2MProvider()
        mcp_client = create_mcp_client(credential_provider=provider)
    """
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from strands.tools.mcp.mcp_client import MCPClient
    except ImportError:
        logger.warning(
            "[GATEWAY] MCP libraries not available - install with: uv add mcp strands-agents-tools"
        )
        return None

    # Auto-discover config if not provided
    config = config or load_config()
    if not config:
        logger.debug("[GATEWAY] Gateway not configured - using embedded tools only")
        return None

    # Use default M2M provider if not specified
    credential_provider = credential_provider or M2MCredentialProvider()

    try:
        logger.info("[GATEWAY] Initiating M2M authentication flow")

        # Obtain access token
        access_token = credential_provider.get_token(config)

        # Create MCP transport with Bearer token
        logger.info(f"[GATEWAY] Connecting to Gateway: {config.endpoint}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        transport = streamablehttp_client(config.endpoint, headers=headers)

        # Create MCP client
        mcp_client = MCPClient(lambda: transport)

        logger.info("[GATEWAY] ✓ MCP client initialized successfully")
        logger.info(f"[GATEWAY]   Endpoint: {config.endpoint}")
        logger.info("[GATEWAY]   Auth mode: M2M OAuth (Client Credentials)")

        return mcp_client

    except Exception as e:
        logger.warning(f"[GATEWAY] ✗ Could not initialize MCP client: {e}")
        logger.info(
            "[GATEWAY] Agent will use embedded tools only (graceful degradation)"
        )
        return None
