#!/usr/bin/env python3
"""Check Gateway OAuth configuration."""

import json
import boto3
from pathlib import Path

# Load gateway outputs
gateway_dir = Path(__file__).parent.parent
with open(gateway_dir / "gateway_outputs.json") as f:
    outputs = json.load(f)

gateway_id = outputs["gateway_id"]
region = outputs.get("region", "us-west-2")

# Get Gateway configuration
client = boto3.client("bedrock-agentcore-control", region_name=region)

try:
    response = client.get_gateway(gatewayIdentifier=gateway_id)
    print(f"\nRaw API Response:")
    print(json.dumps(response, indent=2, default=str))
    print("\n")

    gateway = response["gateway"]

    print("=" * 70)
    print("Gateway OAuth Configuration")
    print("=" * 70)
    print(f"\nGateway ID: {gateway_id}")
    print(f"Gateway ARN: {gateway.get('gatewayArn', 'N/A')}")
    print(f"\nAuthorizer Type: {gateway.get('authorizerType', 'N/A')}")

    if "authorizerConfiguration" in gateway:
        auth_config = gateway["authorizerConfiguration"]
        if "customJWTAuthorizer" in auth_config:
            jwt_config = auth_config["customJWTAuthorizer"]
            print(f"\nOAuth Configuration:")
            print(f"  Discovery URL: {jwt_config.get('discoveryUrl', 'N/A')}")

            allowed_clients = jwt_config.get("allowedClients", [])
            print(f"\n  Allowed Clients ({len(allowed_clients)}):")
            for i, client_id in enumerate(allowed_clients, 1):
                print(f"    {i}. {client_id}")

            # Check if M2M client is in the list
            with open(gateway_dir / "m2m_config.json") as f:
                m2m_config = json.load(f)
            m2m_client_id = m2m_config["client_id"]

            print(f"\n  M2M Client ID: {m2m_client_id}")
            if m2m_client_id in allowed_clients:
                print(f"  ✅ M2M client is in allowedClients list")
            else:
                print(f"  ❌ M2M client is NOT in allowedClients list")
                print(f"  ⚠️  Gateway will reject tokens from M2M client")
        else:
            print("\nNo customJWTAuthorizer configuration found")
    else:
        print("\nNo authorizerConfiguration found")

    print("\n" + "=" * 70)

except Exception as e:
    print(f"❌ Error getting gateway configuration: {e}")
