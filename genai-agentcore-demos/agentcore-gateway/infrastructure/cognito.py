"""
Cognito integration module.

Auto-detects Cognito configuration from finance-personal-assistant deployment.
No new Cognito resources are created - we reuse existing User Pool.
"""
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def detect_cognito_config(agent_dir: Path) -> Optional[Dict]:
    """
    Auto-detect Cognito configuration from agent deployment.

    Reads .bedrock_agentcore.yaml from finance-personal-assistant to extract:
    - Cognito User Pool ID
    - Cognito Client IDs (user auth + M2M)
    - Discovery URL

    Also checks for m2m_config.json for additional M2M client credentials.

    Args:
        agent_dir: Path to finance-personal-assistant directory

    Returns:
        Cognito config dict or None if not found
        Format: {
            'userPoolId': 'us-west-2_...',
            'allowedClients': ['user_client_id', 'm2m_client_id'],
            'discoveryUrl': 'https://cognito-idp...',
            'm2m_client_id': '...',  # Optional: if M2M configured
            'm2m_client_secret': '...'  # Optional: if M2M configured
        }
    """
    try:
        yaml_file = agent_dir / '.bedrock_agentcore.yaml'

        if not yaml_file.exists():
            logger.info("  No .bedrock_agentcore.yaml found - OAuth not configured")
            return None

        # Parse YAML config
        import yaml
        import json
        with open(yaml_file) as f:
            config = yaml.safe_load(f)

        # Navigate to OAuth configuration
        # Check both paths: authorizer_configuration (new SDK) and bedrock_agentcore.oauth (old SDK)
        agent_config = config.get('agents', {}).get('finance_personal_assistant', {})

        authorizer_config = agent_config.get('authorizer_configuration')
        if not authorizer_config:
            oauth = agent_config.get('bedrock_agentcore', {}).get('oauth')
            if not oauth or 'customJWTAuthorizer' not in oauth:
                logger.info("  No OAuth configuration found in agent deployment")
                return None
            jwt_config = oauth['customJWTAuthorizer']
        else:
            jwt_config = authorizer_config.get('customJWTAuthorizer')
            if not jwt_config:
                logger.info("  No OAuth configuration found in agent deployment")
                return None
        discovery_url = jwt_config['discoveryUrl']

        # Extract user pool ID from discovery URL
        # Format: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_XXX/.well-known/...
        user_pool_id = discovery_url.split('/')[-2]

        # Start with user authentication client
        allowed_clients = jwt_config['allowedClients'].copy()

        cognito_config = {
            'userPoolId': user_pool_id,
            'allowedClients': allowed_clients,
            'discoveryUrl': discovery_url
        }

        # Check for M2M configuration
        gateway_dir = agent_dir.parent / 'agentcore-gateway'
        m2m_config_file = gateway_dir / 'm2m_config.json'

        if m2m_config_file.exists():
            with open(m2m_config_file) as f:
                m2m_config = json.load(f)

            m2m_client_id = m2m_config.get('client_id')
            if m2m_client_id and m2m_client_id not in allowed_clients:
                allowed_clients.append(m2m_client_id)

            cognito_config['m2m_client_id'] = m2m_client_id
            cognito_config['m2m_client_secret'] = m2m_config.get('client_secret')
            cognito_config['m2m_scope'] = m2m_config.get('scope')

            logger.info(f"✓ Detected M2M configuration:")
            logger.info(f"  M2M Client ID: {m2m_client_id[:8]}...")
        else:
            logger.info("  No M2M configuration found (m2m_config.json)")

        logger.info(f"✓ Auto-detected Cognito config:")
        logger.info(f"  User Pool: {cognito_config['userPoolId']}")
        logger.info(f"  Allowed Clients: {len(allowed_clients)} client(s)")

        return cognito_config

    except ImportError:
        logger.warning("  PyYAML not installed - cannot parse .bedrock_agentcore.yaml")
        logger.info("  Install with: pip install pyyaml")
        return None

    except Exception as e:
        logger.warning(f"  Could not auto-detect Cognito config: {e}")
        return None


def get_cognito_token(user_pool_domain: str, client_id: str, client_secret: str) -> str:
    """
    Get Cognito access token using client credentials flow.

    Note: This is for testing only. In production, tokens are obtained
    by the frontend application and passed to the agent.

    Args:
        user_pool_domain: Cognito domain (e.g., 'myapp.auth.us-west-2.amazoncognito.com')
        client_id: Cognito app client ID
        client_secret: Cognito app client secret

    Returns:
        Access token string
    """
    import requests
    import base64

    # Encode client credentials
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    # Token endpoint
    token_url = f"https://{user_pool_domain}/oauth2/token"

    response = requests.post(
        token_url,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded}'
        },
        data={
            'grant_type': 'client_credentials'
        }
    )

    response.raise_for_status()
    token_data = response.json()

    return token_data['access_token']
