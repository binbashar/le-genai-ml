#!/usr/bin/env python3
"""
Health check module for AWS Bedrock AgentCore agents.

Provides two testing modes:
- AWS: Test deployed agent via AgentCore Runtime
- Local: Test agent via local HTTP endpoint

Default behavior: Cascading fallback (AWS → Local)
Exit 0 if any mode succeeds, exit 1 if all fail.
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import aiohttp
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

# Import authentication utilities (optional dependency - graceful fallback if not available)
try:
    # Try relative import first (when imported as a module)
    from .auth_utils import (
        authenticate,
        extract_oauth_config_from_yaml,
        invoke_with_token,
    )

    AUTH_UTILS_AVAILABLE = True
except (ImportError, ValueError):
    try:
        # Try absolute import (when run as script or from parent directory)
        from libs.python.auth_utils import (
            authenticate,
            extract_oauth_config_from_yaml,
            invoke_with_token,
        )

        AUTH_UTILS_AVAILABLE = True
    except ImportError:
        AUTH_UTILS_AVAILABLE = False


# Health Check Constants
class HealthCheckConstants:
    """Centralized configuration constants for health checks."""

    # Response validation
    MIN_RESPONSE_LENGTH: int = 10

    # Network configuration
    LOCAL_PORT: int = 8080
    CONNECT_TIMEOUT: int = 20
    PING_TIMEOUT: int = 10
    DEFAULT_TIMEOUT: int = 120

    # AWS configuration
    MAX_RETRY_ATTEMPTS: int = 2
    RETRY_MODE: str = "standard"
    DEFAULT_REGION: str = "us-west-2"

    # Session IDs prefixes
    AWS_SESSION_PREFIX: str = "health-"
    LOCAL_SESSION_PREFIX: str = "health-local-"


class BotoClientFactory(Protocol):
    """Protocol for boto3 client factory functions."""

    def __call__(self, service: str, *, config: Any) -> Any: ...


@dataclass
class HealthCheckCredentials:
    """Credentials for health check authentication.

    Args:
        username: Username for authentication
        password: Password for authentication
        credential_source: Source of credentials (e.g., "demo", "env", "config")
    """

    username: str
    password: str
    credential_source: str = "demo"


@dataclass
class AgentHealthConfig:
    """Configuration for agent health checks.

    Args:
        agent_name: Human-readable name for the agent (must match name in .bedrock_agentcore.yaml)
        agent_dir: Directory containing agent code and .bedrock_agentcore.yaml
        default_prompt: Default test prompt
        aws_profile: AWS profile for authentication
        demo_credentials: Optional demo credentials for testing authenticated agents
    """

    agent_name: str
    agent_dir: str
    default_prompt: str = "Hello, are you operational?"
    aws_profile: str = "binbash"
    demo_credentials: HealthCheckCredentials | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════


def create_health_check_cli(
    config: AgentHealthConfig,
    get_client_func: BotoClientFactory | None = None,
):
    """Create CLI for agent health checks.

    Args:
        config: Agent configuration
        get_client_func: Optional function to create boto3 client
    """
    parser = argparse.ArgumentParser(
        description=f"Health check for {config.agent_name}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--aws",
        action="store_true",
        help="Force AWS mode only (fail if not deployed)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help=f"Force local mode only (test HTTP endpoint at localhost:{HealthCheckConstants.LOCAL_PORT})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=HealthCheckConstants.DEFAULT_TIMEOUT,
        help=f"Response timeout in seconds (default: {HealthCheckConstants.DEFAULT_TIMEOUT})",
    )

    args = parser.parse_args()

    mode_count = sum([args.aws, args.local])
    if mode_count > 1:
        print("❌ Error: Only one mode flag (--aws, --local) can be specified")
        sys.exit(1)

    if args.aws:
        runtime_arn = get_runtime_arn(config)
        if not runtime_arn:
            print(
                "❌ Not deployed: .bedrock_agentcore.yaml not found or missing agent ARN"
            )
            sys.exit(1)
        success = run_health_check_aws(
            config, runtime_arn, timeout=args.timeout, get_client_func=get_client_func
        )
    elif args.local:
        success = asyncio.run(run_health_check_local(config, timeout=args.timeout))
    else:
        success = asyncio.run(
            run_cascading_health_check(config, args.timeout, get_client_func)
        )

    sys.exit(0 if success else 1)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API - CASCADING HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════


async def run_cascading_health_check(
    config: AgentHealthConfig,
    timeout: int,
    get_client_func: BotoClientFactory | None = None,
) -> bool:
    """Try AWS → Local modes in sequence until one succeeds.

    Args:
        config: Agent configuration
        timeout: Response timeout in seconds
        get_client_func: Optional function to create boto3 client

    Returns:
        True if any mode succeeds, False if all fail
    """
    runtime_arn = get_runtime_arn(config)
    if runtime_arn:
        success = run_health_check_aws(config, runtime_arn, timeout, get_client_func)
        if success:
            return True

    success = await run_health_check_local(config, timeout=timeout)
    if success:
        return True

    return False


def _validate_response(response_text: str, elapsed: float) -> bool:
    """Validate response meets minimum requirements.

    Args:
        response_text: The response text to validate
        elapsed: Elapsed time in seconds

    Returns:
        True if response is valid, False otherwise
    """
    if len(response_text) > HealthCheckConstants.MIN_RESPONSE_LENGTH:
        print(f"  ✓ ok [{elapsed:.2f}s]")
        return True
    print(
        f"  ❌ error: response too short ({len(response_text)} chars, minimum {HealthCheckConstants.MIN_RESPONSE_LENGTH}) [{elapsed:.2f}s]"
    )
    return False


def _detect_agent_authentication(agent_dir: str) -> dict | None:
    """Detect OAuth configuration from .bedrock_agentcore.yaml (provider-agnostic).

    Reads JWT authorizer configuration directly from deployment YAML for single source of truth.
    Supports any OAuth2/OIDC provider: Cognito, Auth0, Okta, custom IDPs.

    Args:
        agent_dir: Directory containing .bedrock_agentcore.yaml

    Returns:
        OAuth configuration dict with discovery_url and client_id, or None if no OAuth configured

    Example return value:
        {
            "discovery_url": "https://cognito-idp.us-west-2.amazonaws.com/.../.well-known/openid-configuration",
            "client_id": "abc123...",
            "allowed_clients": ["abc123...", ...]
        }
    """
    if not AUTH_UTILS_AVAILABLE:
        return None

    yaml_path = Path(agent_dir) / ".bedrock_agentcore.yaml"
    return extract_oauth_config_from_yaml(yaml_path)


def _get_health_check_credentials(config: AgentHealthConfig) -> HealthCheckCredentials:
    """Get credentials for health check authentication.

    Retrieves credentials from config or environment variables only.
    Never uses hardcoded defaults for security reasons.

    Args:
        config: Agent health check configuration

    Returns:
        HealthCheckCredentials instance

    Raises:
        ValueError: If credentials are required but not available
    """
    # Priority 1: Use credentials from config
    if config.demo_credentials:
        return config.demo_credentials

    # Priority 2: Check environment variables
    username = os.environ.get("AGENTCORE_HEALTH_USERNAME")
    password = os.environ.get("AGENTCORE_HEALTH_PASSWORD")

    if username and password:
        return HealthCheckCredentials(
            username=username,
            password=password,
            credential_source="environment",
        )

    # No hardcoded credentials for security - fail explicitly
    raise ValueError(
        "Health check credentials required for authenticated agent. "
        "Provide credentials via:\n"
        "  1. AgentHealthConfig.demo_credentials parameter\n"
        "  2. Environment variables: AGENTCORE_HEALTH_USERNAME, AGENTCORE_HEALTH_PASSWORD\n"
    )


def _extract_region_from_arn(runtime_arn: str) -> str:
    """Extract AWS region from AgentCore Runtime ARN.

    Args:
        runtime_arn: AgentCore Runtime ARN (format: arn:aws:bedrock-agentcore:region:...)

    Returns:
        AWS region string

    Raises:
        ValueError: If ARN format is invalid
    """
    try:
        return runtime_arn.split(":")[3]
    except IndexError:
        raise ValueError(f"Invalid AgentCore Runtime ARN format: {runtime_arn}")


def _invoke_with_iam(
    config: AgentHealthConfig,
    runtime_arn: str,
    prompt: str,
    session_id: str,
    start_time: float,
    timeout: int,
    get_client_func: BotoClientFactory | None,
) -> tuple[bool, str, float]:
    """Invoke agent using IAM-based authentication.

    Args:
        config: Agent health check configuration
        runtime_arn: AgentCore Runtime ARN
        prompt: Test prompt to send
        session_id: Unique session identifier
        start_time: Start time for timeout calculation
        timeout: Response timeout in seconds
        get_client_func: Optional boto3 client factory

    Returns:
        Tuple of (success, response_text, elapsed_time)
    """
    client = _create_agentcore_client(config, get_client_func, timeout)

    return _invoke_aws_agent(
        client, runtime_arn, prompt, session_id, start_time, timeout
    )


def _invoke_with_token_auth(
    auth_config: dict,
    credentials: HealthCheckCredentials,
    runtime_arn: str,
    prompt: str,
    session_id: str,
    start_time: float,
    timeout: int,
) -> tuple[bool, str, float]:
    """Invoke agent using token-based authentication.

    Args:
        auth_config: Authentication configuration
        credentials: Health check credentials
        runtime_arn: AgentCore Runtime ARN
        prompt: Test prompt to send
        session_id: Unique session identifier
        start_time: Start time for timeout calculation
        timeout: Response timeout in seconds

    Returns:
        Tuple of (success, response_text, elapsed_time)
    """
    try:
        # Authenticate and get token
        auth_result = authenticate(
            auth_config, credentials.username, credentials.password
        )
        token = auth_result["AccessToken"]

        # Extract region from ARN
        region = _extract_region_from_arn(runtime_arn)

        # Invoke with token
        response = invoke_with_token(
            agent_arn=runtime_arn,
            token=token,
            prompt=prompt,
            session_id=session_id,
            region=region,
            timeout=timeout,
        )

        # Check HTTP status code
        if response.status_code != 200:
            elapsed = time.time() - start_time
            print(
                f"  ❌ HTTP {response.status_code}: {response.text[:200]} [{elapsed:.2f}s]"
            )
            return False, "", elapsed

        # Parse SSE response
        response_text = ""
        for line in response.iter_lines():
            if _check_timeout(start_time, timeout):
                return False, response_text, timeout

            line_str = line.decode("utf-8") if isinstance(line, bytes) else line
            event = parse_sse_event(line_str)

            if not event:
                continue

            # Check for error events
            if isinstance(event, dict) and "error" in event:
                elapsed = time.time() - start_time
                error_type = event.get("error_type", "Error")
                error_msg = event.get("error", "Unknown error")
                print(f"  ❌ Agent error ({error_type}): {error_msg} [{elapsed:.2f}s]")
                return False, "", elapsed

            response_text += _extract_sse_token(event)

        elapsed = time.time() - start_time
        return True, response_text, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Token auth failed ({type(e).__name__}): {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed


def run_health_check_aws(
    config: AgentHealthConfig,
    runtime_arn: str,
    timeout: int = HealthCheckConstants.DEFAULT_TIMEOUT,
    get_client_func: BotoClientFactory | None = None,
) -> bool:
    """Test agent via AWS AgentCore Runtime.

    Automatically detects and uses appropriate authentication method:
    - Token-based (JWT) if agent has .auth_config
    - IAM-based (SigV4) otherwise

    Args:
        config: Agent configuration (may include demo credentials)
        runtime_arn: AgentCore Runtime ARN
        timeout: Response timeout in seconds
        get_client_func: Optional function to create boto3 client

    Returns:
        True if healthy, False otherwise

    Note:
        For token-based authentication, credentials MUST be provided via:
        1. config.demo_credentials parameter
        2. Environment variables (AGENTCORE_HEALTH_USERNAME, AGENTCORE_HEALTH_PASSWORD)

        Health check will fail with clear error if credentials are not available.
    """
    prompt, session_id, start_time = _setup_health_check(
        config, session_prefix=HealthCheckConstants.AWS_SESSION_PREFIX
    )

    try:
        # Detect authentication configuration
        auth_config = _detect_agent_authentication(config.agent_dir)

        if auth_config:
            # Token-based authentication strategy
            credentials = _get_health_check_credentials(config)

            success, response_text, elapsed = _invoke_with_token_auth(
                auth_config=auth_config,
                credentials=credentials,
                runtime_arn=runtime_arn,
                prompt=prompt,
                session_id=session_id,
                start_time=start_time,
                timeout=timeout,
            )
        else:
            # IAM-based authentication strategy
            success, response_text, elapsed = _invoke_with_iam(
                config=config,
                runtime_arn=runtime_arn,
                prompt=prompt,
                session_id=session_id,
                start_time=start_time,
                timeout=timeout,
                get_client_func=get_client_func,
            )

        if not success:
            return False

        return _validate_response(response_text, elapsed)

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Invocation failed: {str(e)} [{elapsed:.2f}s]")
        return False


async def run_health_check_local(
    config: AgentHealthConfig,
    timeout: int = HealthCheckConstants.DEFAULT_TIMEOUT,
) -> bool:
    """Test agent via local HTTP endpoint (configurable port, default: 8080).

    Expects container running via: agentcore launch --local

    Uses /ping endpoint for quick health check, then /invocations for full test.

    Args:
        config: Agent configuration
        timeout: Response timeout in seconds

    Returns:
        True if healthy, False otherwise
    """
    base_url = f"http://localhost:{HealthCheckConstants.LOCAL_PORT}"

    # Pre-flight: Quick ping check
    if not await _check_local_ping(base_url):
        return False

    prompt, session_id, _ = _setup_health_check(
        config, HealthCheckConstants.LOCAL_SESSION_PREFIX
    )

    success, response_text, elapsed = await _invoke_local_agent(
        base_url, prompt, session_id, timeout
    )

    if not success:
        return False

    return _validate_response(response_text, elapsed)


def _invoke_aws_agent(
    client: Any,
    runtime_arn: str,
    prompt: str,
    session_id: str,
    start_time: float,
    timeout: int,
) -> tuple[bool, str, float]:
    """Invoke AWS agent runtime and stream response.

    Mirrors _invoke_local_agent signature pattern for symmetry.

    Args:
        client: Boto3 bedrock-agentcore client
        runtime_arn: AgentCore Runtime ARN
        prompt: The prompt to send
        session_id: Unique session identifier
        start_time: Start time for timeout checking
        timeout: Response timeout in seconds

    Returns:
        Tuple of (success, response_text, elapsed_time)
    """
    try:
        payload = json.dumps({"prompt": prompt, "session_id": session_id})
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=payload,
        )

        response_stream = response.get("response")
        if not response_stream:
            elapsed = time.time() - start_time
            print(f"  ❌ no response stream [{elapsed:.2f}s]")
            return False, "", elapsed

        response_text = ""
        for line in response_stream.iter_lines():
            if _check_timeout(start_time, timeout):
                return False, response_text, timeout

            line_str = line.decode("utf-8") if isinstance(line, bytes) else line
            event = parse_sse_event(line_str)

            if not event:
                continue

            # Check for error events
            if isinstance(event, dict) and "error" in event:
                elapsed = time.time() - start_time
                error_type = event.get("error_type", "Error")
                error_msg = event.get("error", "Unknown error")
                print(f"  ❌ Agent error ({error_type}): {error_msg} [{elapsed:.2f}s]")
                return False, "", elapsed

            response_text += _extract_sse_token(event)

        elapsed = time.time() - start_time
        return True, response_text, elapsed

    except (ClientError, BotoCoreError, EndpointConnectionError) as e:
        elapsed = time.time() - start_time
        print(f"  ❌ AWS error: {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed
    except json.JSONDecodeError as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Invalid response format: {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Unexpected error ({type(e).__name__}): {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed


async def _invoke_local_agent(
    base_url: str,
    prompt: str,
    session_id: str,
    timeout: int,
) -> tuple[bool, str, float]:
    """Invoke local agent and stream response.

    Sends a prompt to the local agent endpoint and streams the response,
    parsing Server-Sent Events (SSE) to extract the agent's reply.

    Args:
        base_url: Base URL of the local endpoint (e.g., http://localhost:8080)
        prompt: The prompt/question to send to the agent
        session_id: Unique session identifier for the conversation
        timeout: Response timeout in seconds

    Returns:
        Tuple of (success, response_text, elapsed_time)
    """
    payload = {"prompt": prompt, "sessionId": session_id}
    start_time = time.time()

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.post(
                f"{base_url}/invocations",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status != 200:
                    elapsed = time.time() - start_time
                    print(f"  ❌ error [{elapsed:.2f}s]")
                    return False, "", elapsed

                full_response = ""
                async for line in resp.content:
                    if _check_timeout(start_time, timeout):
                        return False, full_response, timeout

                    if line.startswith(b"data: "):
                        data_str = line[6:].decode("utf-8").strip()
                        try:
                            event = json.loads(data_str)
                            full_response += _extract_sse_token(event)
                        except json.JSONDecodeError:
                            continue

                elapsed = time.time() - start_time
                return True, full_response, elapsed

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"  ❌ timeout after {timeout}s [{elapsed:.2f}s]")
        return False, "", elapsed
    except aiohttp.ClientError as e:
        elapsed = time.time() - start_time
        print(f"  ❌ HTTP error: {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed
    except json.JSONDecodeError as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Invalid response format: {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Unexpected error ({type(e).__name__}): {str(e)} [{elapsed:.2f}s]")
        return False, "", elapsed


def _setup_health_check(
    config: AgentHealthConfig,
    session_prefix: str = HealthCheckConstants.AWS_SESSION_PREFIX,
) -> tuple[str, str, float]:
    """Setup common health check context.

    Args:
        config: Agent configuration
        session_prefix: Prefix for session ID (e.g., 'health-', 'health-local-')

    Returns:
        Tuple of (prompt, random_session_id, start_time)
    """
    random_session_id = f"{session_prefix}{uuid.uuid4()}"
    print(f"→ {config.agent_name}")
    return config.default_prompt, random_session_id, time.time()


def _create_agentcore_client(
    config: AgentHealthConfig,
    get_client_func: BotoClientFactory | None = None,
    timeout: int = HealthCheckConstants.DEFAULT_TIMEOUT,
) -> Any:
    """Create AgentCore client.

    Args:
        config: Agent configuration
        get_client_func: Optional function to create boto3 client
        timeout: Response timeout in seconds

    Returns:
        AgentCore client
    """
    import boto3

    boto_config = Config(
        region_name=get_region(),
        read_timeout=timeout,
        connect_timeout=HealthCheckConstants.CONNECT_TIMEOUT,
        retries={
            "max_attempts": HealthCheckConstants.MAX_RETRY_ATTEMPTS,
            "mode": HealthCheckConstants.RETRY_MODE,
        },
    )
    if get_client_func:
        return get_client_func("bedrock-agentcore", config=boto_config)
    session = boto3.Session(profile_name=config.aws_profile)
    return session.client("bedrock-agentcore", config=boto_config)


async def _check_local_ping(base_url: str) -> bool:
    """Quick health check of local endpoint.

    Performs a fast pre-flight check to verify the local agent endpoint
    is accessible and healthy before attempting full invocation.

    Args:
        base_url: Base URL of the local endpoint (e.g., http://localhost:8080)

    Returns:
        True if endpoint is healthy, False otherwise
    """
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=HealthCheckConstants.PING_TIMEOUT)
        ) as session:
            async with session.get(f"{base_url}/ping") as resp:
                if resp.status != 200:
                    print(
                        "❌ Local endpoint unhealthy. Run 'agentcore launch --local' first."
                    )
                    return False
                data = await resp.json()
                if data.get("status") != "Healthy":
                    print(f"❌ Agent status: {data.get('status')}")
                    return False
                return True
    except (aiohttp.ClientError, asyncio.TimeoutError):
        print("❌ Local endpoint not accessible. Run 'agentcore launch --local' first.")
        return False
    except Exception as e:
        print(f"❌ Unexpected ping error: {str(e)}")
        return False


def parse_sse_event(line_str: str) -> dict[str, Any] | None:
    """Parse Server-Sent Events (SSE) data from response stream.

    Args:
        line_str: Raw SSE line from stream

    Returns:
        Parsed event dictionary or None if invalid
    """
    if not line_str.startswith("data: "):
        return None

    data_str = line_str[6:]
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        return None


def _check_timeout(start_time: float, timeout: int) -> bool:
    """Check if timeout exceeded and print message.

    Args:
        start_time: Start time in seconds
        timeout: Timeout duration in seconds

    Returns:
        True if timeout exceeded, False otherwise
    """
    if time.time() - start_time > timeout:
        print(f"  ❌ timeout after {timeout}s")
        return True
    return False


def _extract_sse_token(event: dict[str, Any] | str) -> str:
    """Extract token from SSE event.

    Args:
        event: SSE event dictionary or string

    Returns:
        Extracted token string
    """
    if isinstance(event, dict) and event.get("type") == "stream_token":
        return event.get("token", "")
    if isinstance(event, str):
        return event
    return ""


def get_runtime_arn(config: AgentHealthConfig) -> str | None:
    """Read AgentCore Runtime ARN from .bedrock_agentcore.yaml.

    Args:
        config: Agent configuration

    Returns:
        Runtime ARN or None if not deployed
    """
    import yaml

    config_file = Path(config.agent_dir) / ".bedrock_agentcore.yaml"

    if not config_file.exists():
        return None

    try:
        with open(config_file) as f:
            yaml_config = yaml.safe_load(f)

        # Navigate YAML structure: agents.{agent_name}.bedrock_agentcore.agent_arn
        if "agents" in yaml_config:
            # Try config.agent_name first, then fall back to default_agent
            agent_name = config.agent_name
            if (
                agent_name not in yaml_config["agents"]
                and "default_agent" in yaml_config
            ):
                agent_name = yaml_config["default_agent"]

            if (
                agent_name in yaml_config["agents"]
                and "bedrock_agentcore" in yaml_config["agents"][agent_name]
                and "agent_arn"
                in yaml_config["agents"][agent_name]["bedrock_agentcore"]
            ):
                return yaml_config["agents"][agent_name]["bedrock_agentcore"][
                    "agent_arn"
                ]

        return None
    except Exception:
        return None


def get_region() -> str:
    """Get AWS region with standard precedence order.

    Returns:
        AWS region name
    """
    import boto3

    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or boto3.Session().region_name
        or HealthCheckConstants.DEFAULT_REGION
    )
