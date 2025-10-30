#!/usr/bin/env python3
"""
Create M2M (Machine-to-Machine) Cognito App Client for Gateway authentication.

This script creates a new App Client in the existing Cognito User Pool
configured for Client Credentials flow (OAuth 2.0 M2M pattern).

Configuration:
    User Pool ID: Auto-detected from {agent}/.bedrock_agentcore.yaml
    Region: AWS_REGION environment variable (default: boto3 session or us-west-2)
    Domain Prefix: COGNITO_DOMAIN_PREFIX environment variable (default: agentcore-gateway)

Usage:
    python setup_m2m_client.py --agent finance-personal-assistant
    python setup_m2m_client.py --agent market-trends-agent

Arguments:
    --agent: Agent directory name (required)

Environment Variables:
    AWS_REGION: AWS region (optional, auto-detected if not set)
    COGNITO_DOMAIN_PREFIX: Cognito domain prefix (optional, uses default if not set)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import boto3

# Configuration (AWS SDK-style with auto-detection)
REGION = os.getenv("AWS_REGION", boto3.Session().region_name or "us-west-2")
COGNITO_DOMAIN_PREFIX = os.getenv("COGNITO_DOMAIN_PREFIX", "agentcore-gateway")
M2M_CLIENT_NAME = "agentcore-gateway-m2m"
RESOURCE_SERVER_ID = "agentcore-gateway"
CUSTOM_SCOPE_NAME = "access"


def detect_user_pool_id(agent_name: str) -> str:
    """
    Auto-detect Cognito User Pool ID from agent deployment.

    Reads .bedrock_agentcore.yaml from specified agent to extract
    User Pool ID from OAuth configuration.

    Args:
        agent_name: Agent directory name (e.g., "finance-personal-assistant")

    Returns:
        User Pool ID (e.g., us-west-2_XXX)

    Raises:
        SystemExit: If user pool cannot be detected
    """
    try:
        # Navigate to agent directory
        agent_dir = Path(__file__).parent.parent.parent / agent_name
        yaml_file = agent_dir / ".bedrock_agentcore.yaml"

        if not yaml_file.exists():
            print(f"❌ No .bedrock_agentcore.yaml found in {agent_name}")
            print(
                f"   Deploy agent with OAuth first: cd {agent_name} && ./configure.sh && ./launch.sh"
            )
            sys.exit(1)

        # Parse YAML config
        import yaml

        with open(yaml_file) as f:
            config = yaml.safe_load(f)

        # Convert agent directory name to config key (replace hyphens with underscores)
        agent_config_key = agent_name.replace("-", "_")

        # Navigate to OAuth configuration
        agent_config = config.get("agents", {}).get(agent_config_key, {})

        # Check both paths: authorizer_configuration (new SDK) and bedrock_agentcore.oauth (old SDK)
        authorizer_config = agent_config.get("authorizer_configuration")
        if not authorizer_config:
            oauth = agent_config.get("bedrock_agentcore", {}).get("oauth")
            if not oauth or "customJWTAuthorizer" not in oauth:
                print(f"❌ No OAuth configuration found in {agent_name} deployment")
                print(
                    f"   Deploy Cognito stack first: cd {agent_name}/cdk && ./deploy.sh"
                )
                sys.exit(1)
            jwt_config = oauth["customJWTAuthorizer"]
        else:
            jwt_config = authorizer_config.get("customJWTAuthorizer")
            if not jwt_config:
                print(f"❌ No OAuth configuration found in {agent_name} deployment")
                print(
                    f"   Deploy Cognito stack first: cd {agent_name}/cdk && ./deploy.sh"
                )
                sys.exit(1)

        discovery_url = jwt_config["discoveryUrl"]

        # Extract user pool ID from discovery URL
        # Format: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_XXX/.well-known/...
        user_pool_id = discovery_url.split("/")[-2]

        print(f"✓ Auto-detected User Pool: {user_pool_id}")
        return user_pool_id

    except ImportError:
        print("❌ PyYAML not installed")
        print("   Install with: pip install pyyaml")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Could not auto-detect User Pool ID: {e}")
        print(f"   Deploy Cognito stack first: cd {agent_name}/cdk && ./deploy.sh")
        sys.exit(1)


def create_cognito_domain(cognito_client, user_pool_id: str):
    """Create Cognito domain for OAuth endpoints if it doesn't exist."""
    try:
        # Check if domain exists
        pool_info = cognito_client.describe_user_pool(UserPoolId=user_pool_id)
        if pool_info["UserPool"].get("Domain"):
            print(
                f"ℹ️  Cognito domain already exists: {pool_info['UserPool']['Domain']}"
            )
            return pool_info["UserPool"]["Domain"]

        # Create domain
        cognito_client.create_user_pool_domain(
            Domain=COGNITO_DOMAIN_PREFIX, UserPoolId=user_pool_id
        )
        print(f"✅ Created Cognito domain: {COGNITO_DOMAIN_PREFIX}")
        return COGNITO_DOMAIN_PREFIX

    except cognito_client.exceptions.InvalidParameterException as e:
        if "Domain already associated" in str(e):
            print(f"ℹ️  Cognito domain already exists: {COGNITO_DOMAIN_PREFIX}")
            return COGNITO_DOMAIN_PREFIX
        raise


def create_resource_server(cognito_client, user_pool_id: str):
    """Create resource server with custom scope for M2M access."""
    try:
        cognito_client.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=RESOURCE_SERVER_ID,
            Name="AgentCore Gateway",
            Scopes=[
                {
                    "ScopeName": CUSTOM_SCOPE_NAME,
                    "ScopeDescription": "Access to AgentCore Gateway tools",
                }
            ],
        )
        print(f"✅ Created resource server: {RESOURCE_SERVER_ID}")
        return f"{RESOURCE_SERVER_ID}/{CUSTOM_SCOPE_NAME}"
    except cognito_client.exceptions.InvalidParameterException as e:
        if "already exists" in str(e):
            print(f"ℹ️  Resource server already exists: {RESOURCE_SERVER_ID}")
            return f"{RESOURCE_SERVER_ID}/{CUSTOM_SCOPE_NAME}"
        raise


def create_m2m_client(cognito_client, user_pool_id: str, custom_scope: str, domain: str):
    """Create M2M app client with Client Credentials flow."""
    try:
        response = cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=M2M_CLIENT_NAME,
            GenerateSecret=True,
            AllowedOAuthFlows=["client_credentials"],
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthScopes=[custom_scope],
            ExplicitAuthFlows=[],  # No user-based auth flows
            PreventUserExistenceErrors="ENABLED",
        )

        client_data = response["UserPoolClient"]
        client_id = client_data["ClientId"]

        # Get client secret (requires separate API call)
        secret_response = cognito_client.describe_user_pool_client(
            UserPoolId=user_pool_id, ClientId=client_id
        )
        client_secret = secret_response["UserPoolClient"]["ClientSecret"]

        print("\n✅ M2M App Client Created Successfully!\n")
        print(f"Client ID: {client_id}")
        print(f"Client Secret: {client_secret}")
        print(f"Allowed Scope: {custom_scope}\n")

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": custom_scope,
            "token_endpoint": f"https://{domain}.auth.{REGION}.amazoncognito.com/oauth2/token",
        }

    except cognito_client.exceptions.InvalidParameterException as e:
        if "already exists" in str(e) or "ClientName" in str(e):
            print(f"❌ M2M client already exists: {M2M_CLIENT_NAME}")
            print("   Delete it first or use the existing credentials.")
            return None
        raise


def save_m2m_config(m2m_config):
    """Save M2M configuration to JSON file for agent to use."""
    output_file = Path(__file__).parent.parent / "m2m_config.json"

    with open(output_file, "w") as f:
        json.dump(m2m_config, f, indent=2)

    print(f"📝 Configuration saved to: {output_file}")
    print("\n⚠️  IMPORTANT: Keep m2m_config.json secure (contains client secret)")
    print("   Add to .gitignore if not already present\n")


def main():
    """Main execution flow."""
    # Parse CLI arguments
    parser = argparse.ArgumentParser(
        description="Create M2M Cognito client for AgentCore Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_m2m_client.py --agent finance-personal-assistant
  python setup_m2m_client.py --agent market-trends-agent
        """,
    )
    parser.add_argument(
        "--agent",
        required=True,
        help="Agent directory name (e.g., finance-personal-assistant)",
    )
    args = parser.parse_args()

    print("🚀 Setting up M2M Authentication for AgentCore Gateway\n")
    print(f"Target Agent: {args.agent}\n")

    # Auto-detect User Pool ID from agent deployment
    print("Step 0: Auto-detecting Cognito User Pool...")
    user_pool_id = detect_user_pool_id(args.agent)

    cognito_client = boto3.client("cognito-idp", region_name=REGION)

    # Step 1: Create Cognito domain (required for OAuth endpoints)
    print("\nStep 1: Creating Cognito domain...")
    domain = create_cognito_domain(cognito_client, user_pool_id)

    # Step 2: Create resource server with custom scope
    print("\nStep 2: Creating resource server...")
    custom_scope = create_resource_server(cognito_client, user_pool_id)

    # Step 3: Create M2M app client
    print("\nStep 3: Creating M2M app client...")
    m2m_config = create_m2m_client(cognito_client, user_pool_id, custom_scope, domain)

    if m2m_config:
        # Step 4: Save configuration
        print("\nStep 4: Saving configuration...")
        save_m2m_config(m2m_config)

        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Update Gateway configuration with this Client ID:")
        print(f"   allowedClients: ['{m2m_config['client_id']}']")
        print("\n2. Update agent code to use GatewayClient SDK:")
        print("   See agentcore-gateway/gateway-specs/07-agent-refactoring.md")
        print("\n3. Redeploy Gateway: cd infrastructure && python gateway.py")
        print("4. Test authentication: cd ../scripts && python test_gateway.py")
        print("=" * 60)


if __name__ == "__main__":
    main()
