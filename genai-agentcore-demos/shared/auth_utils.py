"""
OAuth2 Authentication Utilities for AgentCore agents.

Uses standard OAuth2 Resource Owner Password Credentials (ROPC) flow (RFC 6749).
Configuration read from .bedrock_agentcore.yaml.
"""

import json
import logging
import re
from pathlib import Path

import jwt
import requests

logger = logging.getLogger(__name__)

# Try to import boto3 (optional dependency for Cognito fallback)
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.debug("boto3 not available - Cognito fallback disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API - CONFIGURATION EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════


def extract_oauth_config_from_ssm(
    agent_name: str,
    region: str = "us-west-2",
) -> dict | None:
    """
    Extract OAuth2 configuration from SSM Parameter Store (AWS best practice).

    This is the recommended method for production deployments as it provides:
    - Repository isolation (no file dependencies)
    - Cross-account/cross-region support
    - Single source of truth (CDK → SSM → All services)
    - Versioning and audit trail
    - IAM-based access control

    Args:
        agent_name: Agent name (e.g., "finance_personal_assistant", "market_trends_agent")
        region: AWS region where SSM parameter is stored (default: us-west-2)

    Returns:
        OAuth configuration dict:
        {
            "discovery_url": "https://.../.well-known/openid-configuration",
            "client_id": "abc123...",
            "allowed_clients": ["abc123...", ...]
        }
        Returns None if parameter not found or no OAuth configured.

    Raises:
        None - returns None on any error for graceful fallback

    Example:
        >>> config = extract_oauth_config_from_ssm("finance_personal_assistant")
        >>> if config:
        ...     token = authenticate(config, "user", "pass")

    SSM Parameter Path:
        /agentcore/{agent_name}/config

    SSM Parameter Format (Unified config):
        {
            "arn": "arn:aws:...",  # Optional, added by post_agent_deploy.py
            "oauth": {              # Optional, added by Cognito CDK
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://...",
                    "allowedClients": ["client-id"]
                }
            }
        }
    """
    if not BOTO3_AVAILABLE:
        logger.debug("boto3 not available - SSM config extraction disabled")
        return None

    try:
        ssm = boto3.client("ssm", region_name=region)

        # Read unified config from SSM Parameter Store
        parameter_name = f"/agentcore/{agent_name}/config"
        logger.debug(f"Reading unified config from SSM: {parameter_name}")

        response = ssm.get_parameter(Name=parameter_name)
        parameter_value = response["Parameter"]["Value"]

        # Parse JSON value
        config_json = json.loads(parameter_value)

        # Extract OAuth section from unified config
        oauth_section = config_json.get("oauth", {})
        jwt_auth = oauth_section.get("customJWTAuthorizer")

        if not jwt_auth:
            logger.debug(f"No OAuth configuration in SSM parameter: {parameter_name}")
            return None

        # Extract standard fields
        discovery_url = jwt_auth.get("discoveryUrl")
        allowed_clients = jwt_auth.get("allowedClients", [])

        if not discovery_url or not allowed_clients:
            logger.debug(f"Incomplete OAuth config in SSM: {parameter_name}")
            return None

        # Normalize to standard format
        oauth_config = {
            "discovery_url": discovery_url,
            "client_id": allowed_clients[0],  # Primary client ID
            "allowed_clients": allowed_clients,
        }

        logger.debug(
            f"Successfully loaded OAuth config from SSM for agent: {agent_name}"
        )
        return oauth_config

    except ssm.exceptions.ParameterNotFound:
        logger.debug(f"SSM parameter not found: /agentcore/{agent_name}/config")
        return None
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        logger.debug(f"Error parsing OAuth config from SSM: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error reading OAuth config from SSM: {e}")
        return None


def extract_oauth_config_from_yaml(yaml_path: Path) -> dict | None:
    """
    Extract OAuth2 configuration from .bedrock_agentcore.yaml.


    Args:
        yaml_path: Path to .bedrock_agentcore.yaml file

    Returns:
        OAuth configuration dict:
        {
            "discovery_url": "https://.../.well-known/openid-configuration",
            "client_id": "abc123...",
            "allowed_clients": ["abc123...", ...]  # all allowed clients
        }
        Returns None if no OAuth configuration found.

    Example YAML structure (works for any provider):
        agents:
          agent_name:
            authorizer_configuration:
              customJWTAuthorizer:
                discoveryUrl: https://idp.example.com/.well-known/openid-configuration
                allowedClients:
                  - client-id-1
                  - client-id-2
    """
    if not yaml_path.exists():
        logger.debug(f"YAML config not found: {yaml_path}")
        return None

    try:
        import yaml

        with open(yaml_path) as f:
            yaml_config = yaml.safe_load(f)

        # Navigate to agents section
        if "agents" not in yaml_config:
            logger.debug("No agents section in YAML")
            return None

        # Find first agent with OAuth configured
        for agent_name, agent_config in yaml_config["agents"].items():
            authorizer = agent_config.get("authorizer_configuration")
            if not authorizer:
                continue

            jwt_auth = authorizer.get("customJWTAuthorizer")
            if not jwt_auth:
                continue

            # Extract standard OpenID Connect fields
            discovery_url = jwt_auth.get("discoveryUrl")
            allowed_clients = jwt_auth.get("allowedClients", [])

            if not discovery_url or not allowed_clients:
                logger.debug(f"Incomplete OAuth config for agent: {agent_name}")
                continue

            logger.debug(f"Found OAuth config for agent: {agent_name}")
            return {
                "discovery_url": discovery_url,
                "client_id": allowed_clients[0],  # Primary client ID
                "allowed_clients": allowed_clients,
            }

        logger.debug("No OAuth configuration found in any agent")
        return None

    except Exception as e:
        logger.debug(f"Error extracting OAuth config from YAML: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API - AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════


def decode_jwt_token(token: str) -> dict:
    """Decode JWT token without signature verification.

    AgentCore Runtime validates the token signature, so we skip verification
    here to avoid needing JWKS keys.

    Args:
        token: JWT access token

    Returns:
        Decoded token claims dict

    Raises:
        ValueError: If token cannot be decoded

    Example:
        >>> decoded = decode_jwt_token(access_token)
        >>> user_id = decoded.get("sub")
        >>> username = decoded.get("cognito:username")
    """
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        logger.debug(f"Decoded JWT claims: {list(decoded.keys())}")
        return decoded
    except jwt.PyJWTError as e:
        raise ValueError(f"Failed to decode JWT token: {e}")


def extract_user_id_from_token(token: str) -> str:
    """Extract username from JWT token.

    For Cognito tokens: Prefers 'username' claim (access tokens) over 'sub' (UUID).
    For other providers: Falls back to 'cognito:username' (ID tokens) or 'sub'.

    Args:
        token: JWT access token

    Returns:
        Username from token claims (e.g., "broker_demo")

    Raises:
        ValueError: If no username/sub claim found

    Example:
        >>> user_id = extract_user_id_from_token(access_token)
        >>> print(user_id)  # e.g., "broker_demo"
    """
    decoded = decode_jwt_token(token)

    # Try username claim first (Cognito access tokens)
    user_id = decoded.get("username")

    # Fallback to cognito:username claim (Cognito ID tokens)
    if not user_id:
        user_id = decoded.get("cognito:username")

    # Final fallback to sub claim (UUID - stable but not human-readable)
    if not user_id:
        user_id = decoded.get("sub")

    if not user_id:
        raise ValueError("JWT token missing username/sub claim")

    logger.info(f"[AUTH] Extracted user_id from JWT: {user_id}")
    return user_id


def authenticate_with_oauth2(
    discovery_url: str,
    client_id: str,
    username: str,
    password: str,
    client_secret: str | None = None,
    scopes: list[str] | None = None,
) -> dict:
    """
    Authenticate using standard OAuth2 Resource Owner Password Credentials (ROPC) flow.

    Uses OpenID Connect discovery to automatically find token endpoint.

    Args:
        discovery_url: OIDC discovery URL (e.g., https://idp.example.com/.well-known/openid-configuration)
        client_id: OAuth2 client identifier
        username: User's username
        password: User's password
        client_secret: Optional client secret (required for confidential clients)
        scopes: Optional list of OAuth2 scopes (e.g., ["openid", "profile"])

    Returns:
        Token response dict:
        {
            "access_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "...",  # optional
            "id_token": "...",  # optional
            "scope": "openid profile",  # optional
        }

    Raises:
        requests.HTTPError: If authentication fails
        ValueError: If discovery or token endpoint is invalid

    Example:
        >>> token_response = authenticate_with_oauth2(
        ...     discovery_url="https://cognito-idp.us-west-2.amazonaws.com/us-west-2_ABC/.well-known/openid-configuration",
        ...     client_id="abc123",
        ...     username="testuser",
        ...     password="password123"
        ... )
        >>> access_token = token_response["access_token"]
    """
    # Step 1: Fetch OIDC discovery document to get token endpoint
    logger.debug(f"Fetching OIDC discovery from: {discovery_url}")
    discovery_doc = _fetch_oidc_discovery(discovery_url)
    token_endpoint = discovery_doc.get("token_endpoint")

    if not token_endpoint:
        raise ValueError(
            f"No token_endpoint in OIDC discovery document: {discovery_url}"
        )

    logger.debug(f"Token endpoint: {token_endpoint}")

    # Step 2: Execute OAuth2 password grant
    return _oauth2_password_grant(
        token_endpoint=token_endpoint,
        client_id=client_id,
        username=username,
        password=password,
        client_secret=client_secret,
        scopes=scopes,
    )


def authenticate(auth_config: dict, username: str, password: str) -> dict:
    """
    High-level authentication function with automatic provider detection.

    Auto-detects authentication method from config and tries:
    1. Standard OAuth2 (preferred, provider-agnostic)
    2. Cognito boto3 fallback (for compatibility with public clients)

    Args:
        auth_config: Auth configuration dict with either:
            - discovery_url + client_id (from extract_oauth_config_from_yaml)
            - provider + user_pool_id + client_id (legacy format)
        username: User's username
        password: User's password

    Returns:
        Authentication result dict with at minimum:
        {
            "AccessToken": "eyJ...",  # JWT access token
            "ExpiresIn": 3600,
            "TokenType": "Bearer"
        }

    Raises:
        ValueError: If authentication fails or config is invalid

    Example:
        >>> config = extract_oauth_config_from_yaml(Path(".bedrock_agentcore.yaml"))
        >>> auth_result = authenticate(config, "testuser", "password123")
        >>> token = auth_result["AccessToken"]
    """
    discovery_url = auth_config.get("discovery_url")

    if discovery_url:
        # Standard OAuth2 flow (preferred)
        try:
            logger.debug("Attempting standard OAuth2 authentication")
            token_response = authenticate_with_oauth2(
                discovery_url=discovery_url,
                client_id=auth_config["client_id"],
                username=username,
                password=password,
                client_secret=auth_config.get("client_secret"),
                scopes=auth_config.get("scopes"),
            )

            # Normalize response format (OAuth2 → Cognito format for compatibility)
            return {
                "AccessToken": token_response["access_token"],
                "ExpiresIn": token_response.get("expires_in", 3600),
                "TokenType": token_response.get("token_type", "Bearer"),
                "RefreshToken": token_response.get("refresh_token"),
                "IdToken": token_response.get("id_token"),
            }

        except Exception as oauth_error:
            logger.debug(f"OAuth2 authentication failed: {oauth_error}")

            # Fallback to Cognito boto3 if discovery URL is Cognito
            if "cognito-idp" in discovery_url and "amazonaws.com" in discovery_url:
                logger.debug("Attempting Cognito boto3 fallback")
                cognito_details = _extract_cognito_details_from_discovery_url(
                    discovery_url
                )

                if cognito_details:
                    return _authenticate_cognito_boto3(
                        user_pool_id=cognito_details["user_pool_id"],
                        client_id=auth_config["client_id"],
                        username=username,
                        password=password,
                        region=cognito_details["region"],
                    )

            # Re-raise original OAuth error if no fallback available
            raise oauth_error

    # Legacy format with explicit provider (backwards compatibility)
    provider = auth_config.get("provider")
    if provider == "cognito":
        logger.debug("Using legacy Cognito authentication")
        return _authenticate_cognito_boto3(
            user_pool_id=auth_config["user_pool_id"],
            client_id=auth_config["client_id"],
            username=username,
            password=password,
            region=auth_config.get("region")
            or auth_config["user_pool_id"].split("_")[0],
        )

    raise ValueError(
        "Invalid auth_config: must contain 'discovery_url' or 'provider' field"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API - AGENT INVOCATION
# ═══════════════════════════════════════════════════════════════════════════════


def invoke_with_token(
    agent_arn: str,
    token: str,
    prompt: str,
    session_id: str,
    region: str,
    timeout: int = 120,
    image_base64: str = None,
    document_base64: str = None,
    filename: str = None,
) -> requests.Response:
    """
    Invoke AgentCore Runtime with bearer token (HTTP invocation).

    Automatically extracts user ID from JWT token's 'sub' claim and passes it
    in the X-Amzn-Bedrock-AgentCore-Runtime-User-Id header for memory isolation.

    Args:
        agent_arn: Agent runtime ARN
        token: Bearer token (JWT from OAuth provider)
        prompt: User prompt
        session_id: Session ID for conversation context (min 33 chars, auto-generated if too short)
        region: AWS region
        timeout: Request timeout in seconds

    Returns:
        Response object with streaming capability

    Raises:
        requests.HTTPError: If invocation fails
        ValueError: If JWT token is invalid or missing 'sub' claim

    Example:
        >>> response = invoke_with_token(
        ...     agent_arn="arn:aws:bedrock-agentcore:...",
        ...     token=auth_result["AccessToken"],
        ...     prompt="Hello, agent!",
        ...     session_id="test-session",
        ...     region="us-west-2"
        ... )
        >>> for line in response.iter_lines():
        ...     print(line)
    """
    import urllib.parse
    import uuid

    # Extract user ID from JWT token
    user_id = extract_user_id_from_token(token)

    # Ensure session_id meets AWS minimum length requirement (33 chars)
    if len(session_id) < 33:
        session_id = f"{session_id}-{uuid.uuid4()}"
        logger.debug(f"Generated session ID: {session_id}")

    # URL-encode the ARN
    arn_encoded = urllib.parse.quote(agent_arn, safe="")

    # Construct endpoint URL
    url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{arn_encoded}/invocations"

    # Headers with bearer token and user ID as custom header
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id": user_id,
    }

    # Query parameters
    params = {"qualifier": "DEFAULT"}

    # Request payload (actor_id in both header AND payload for reliability)
    payload = {
        "prompt": prompt,
        "actor_id": user_id,  # Pass actor_id in payload (works for both OAuth and IAM)
    }

    # Add image if provided (vision capability)
    if image_base64:
        payload["image_base64"] = image_base64
        logger.info(f"Image included in payload (size: {len(image_base64)} bytes)")

    # Add document if provided (PDF/CSV support)
    if document_base64 and filename:
        payload["document_base64"] = document_base64
        payload["filename"] = filename
        logger.info(f"Document included in payload: {filename} (size: {len(document_base64)} bytes)")

    logger.info(f"Invoking agent via HTTP: {url}")
    logger.info(f"User ID: {user_id}, Session ID: {session_id}")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Payload keys: {list(payload.keys())}")

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


# ═══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS - OAUTH2 STANDARD FLOW
# ═══════════════════════════════════════════════════════════════════════════════


def _fetch_oidc_discovery(discovery_url: str) -> dict:
    """
    Fetch OpenID Connect discovery document.

    Args:
        discovery_url: OIDC discovery URL (.well-known/openid-configuration)

    Returns:
        Discovery document dict with endpoints and configuration

    Raises:
        requests.HTTPError: If discovery endpoint is unreachable
        ValueError: If response is not valid JSON
    """
    response = requests.get(discovery_url, timeout=10)
    response.raise_for_status()
    return response.json()


def _oauth2_password_grant(
    token_endpoint: str,
    client_id: str,
    username: str,
    password: str,
    client_secret: str | None = None,
    scopes: list[str] | None = None,
) -> dict:
    """
    Execute OAuth2 Resource Owner Password Credentials (ROPC) grant (RFC 6749 Section 4.3).

    Args:
        token_endpoint: OAuth2 token endpoint URL
        client_id: OAuth2 client identifier
        username: Resource owner username
        password: Resource owner password
        client_secret: Optional client secret (required for confidential clients)
        scopes: Optional list of scopes to request

    Returns:
        Token response dict from provider

    Raises:
        requests.HTTPError: If token request fails
    """
    # Build request payload (application/x-www-form-urlencoded)
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
    }

    if client_secret:
        data["client_secret"] = client_secret

    if scopes:
        data["scope"] = " ".join(scopes)

    # POST to token endpoint
    logger.debug(f"Requesting token from: {token_endpoint}")
    response = requests.post(token_endpoint, data=data, timeout=30)

    # Raise for HTTP errors (401, 403, etc.)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # Include error details from provider if available
        try:
            error_data = response.json()
            error_msg = error_data.get(
                "error_description", error_data.get("error", str(e))
            )
            raise requests.HTTPError(f"OAuth2 token request failed: {error_msg}") from e
        except ValueError:
            raise e

    return response.json()


# ═══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS - COGNITO FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════


def _authenticate_cognito_boto3(
    user_pool_id: str,
    client_id: str,
    username: str,
    password: str,
    region: str,
) -> dict:
    """
    Authenticate with Amazon Cognito using boto3 SDK (fallback for public clients).

    Used as fallback when standard OAuth2 fails (typically public clients without secret).
    Requires boto3 package to be installed.

    Args:
        user_pool_id: Cognito user pool ID (e.g., us-west-2_ABC123)
        client_id: Cognito app client ID
        username: Cognito username
        password: User password
        region: AWS region

    Returns:
        AuthenticationResult dict:
        {
            "AccessToken": "eyJ...",
            "ExpiresIn": 3600,
            "TokenType": "Bearer",
            "RefreshToken": "...",
            "IdToken": "..."
        }

    Raises:
        ValueError: If authentication fails or boto3 not available
    """
    if not BOTO3_AVAILABLE:
        raise ValueError(
            "boto3 is required for Cognito fallback authentication. "
            "Install with: pip install boto3"
        )

    try:
        cognito_client = boto3.client("cognito-idp", region_name=region)

        response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )

        return response["AuthenticationResult"]

    except cognito_client.exceptions.NotAuthorizedException as e:
        raise ValueError(f"Invalid username or password: {e}") from e
    except cognito_client.exceptions.UserNotFoundException as e:
        raise ValueError(f"User not found: {e}") from e
    except KeyError as e:
        raise ValueError(f"Missing required config field: {e}") from e
    except Exception as e:
        logger.error(f"Cognito boto3 authentication error: {e}")
        raise ValueError(f"Cognito authentication failed: {e}") from e


def _extract_cognito_details_from_discovery_url(discovery_url: str) -> dict | None:
    """
    Extract region and user pool ID from Cognito discovery URL.

    Args:
        discovery_url: Cognito OIDC discovery URL

    Returns:
        Dict with region and user_pool_id, or None if not a valid Cognito URL

    Example:
        >>> url = "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_ABC123/.well-known/openid-configuration"
        >>> _extract_cognito_details_from_discovery_url(url)
        {"region": "us-west-2", "user_pool_id": "us-west-2_ABC123"}
    """
    # Pattern: https://cognito-idp.REGION.amazonaws.com/POOL_ID/.well-known/...
    match = re.match(
        r"https://cognito-idp\.([^.]+)\.amazonaws\.com/([^/]+)/", discovery_url
    )

    if not match:
        return None

    return {
        "region": match.group(1),
        "user_pool_id": match.group(2),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES - DEPLOYMENT AND CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


def configure_agent_auth(
    agentcore_client,
    runtime_arn: str,
    auth_config: dict,
) -> None:
    """
    Configure authentication for AgentCore Runtime (deployment helper).

    Args:
        agentcore_client: boto3 bedrock-agentcore-control client
        runtime_arn: Agent runtime ARN
        auth_config: Auth configuration dict with discovery_url and client_id

    Raises:
        ValueError: If configuration is invalid
    """
    if "discovery_url" not in auth_config or "client_id" not in auth_config:
        raise ValueError(
            "auth_config must contain 'discovery_url' and 'client_id' fields"
        )

    # Extract runtime ID from ARN
    runtime_id = runtime_arn.split("/")[-1]

    # Get current runtime configuration
    logger.info("Retrieving current runtime configuration...")
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

    logger.info("✅ Configured OAuth authentication for agent")
    logger.info(f"   Discovery URL: {auth_config['discovery_url']}")
    logger.info(f"   Client ID: {auth_config['client_id']}")


def get_auth_mode(yaml_path: Path) -> str:
    """
    Get authentication mode for an agent from .bedrock_agentcore.yaml.

    Args:
        yaml_path: Path to .bedrock_agentcore.yaml file

    Returns:
        "oauth" if OAuth configured, "iam" otherwise
    """
    oauth_config = extract_oauth_config_from_yaml(yaml_path)
    return "oauth" if oauth_config else "iam"
