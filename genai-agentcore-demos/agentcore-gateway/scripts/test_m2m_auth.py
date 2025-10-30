#!/usr/bin/env python3
"""
Test M2M (Machine-to-Machine) authentication with Gateway.

This script:
1. Obtains M2M access token via Client Credentials flow
2. Tests Gateway endpoints with M2M token
3. Verifies JWT validation is working correctly
"""

import base64
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Required libraries not installed")
    print("Install with: pip install requests")
    sys.exit(1)


def load_m2m_config():
    """Load M2M configuration from m2m_config.json"""
    config_file = Path(__file__).parent.parent / "m2m_config.json"

    if not config_file.exists():
        print("❌ M2M configuration not found")
        print("Run first: python scripts/setup_m2m_client.py")
        sys.exit(1)

    with open(config_file) as f:
        return json.load(f)


def load_gateway_outputs():
    """Load Gateway deployment outputs"""
    outputs_file = Path(__file__).parent.parent / "gateway_outputs.json"

    if not outputs_file.exists():
        print("❌ Gateway not deployed")
        print("Run first: python deploy.py")
        sys.exit(1)

    with open(outputs_file) as f:
        return json.load(f)


def get_m2m_access_token(m2m_config):
    """Obtain M2M access token using Client Credentials flow"""
    print("\n" + "=" * 70)
    print("Step 1: Obtain M2M Access Token")
    print("=" * 70)

    client_id = m2m_config["client_id"]
    client_secret = m2m_config["client_secret"]
    token_endpoint = m2m_config["token_endpoint"]
    scope = m2m_config.get("scope")

    # Encode client credentials as Basic auth
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    print(f"\nToken Endpoint: {token_endpoint}")
    print(f"Client ID: {client_id[:8]}...")
    print(f"Scope: {scope}")

    # Request token via Client Credentials flow
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }

    data = {"grant_type": "client_credentials"}
    if scope:
        data["scope"] = scope

    try:
        response = requests.post(token_endpoint, headers=headers, data=data, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data["access_token"]

        print(f"\n✅ Access token obtained successfully")
        print(f"   Token type: {token_data.get('token_type', 'Bearer')}")
        print(f"   Expires in: {token_data.get('expires_in', 'N/A')} seconds")
        print(f"   Token preview: {access_token[:20]}...")

        return access_token

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to obtain access token: {e}")
        if hasattr(e.response, "text"):
            print(f"   Response: {e.response.text}")
        sys.exit(1)


def test_tools_list(gateway_endpoint, access_token):
    """Test tools/list with M2M authentication"""
    print("\n" + "=" * 70)
    print("Step 2: Test tools/list with M2M Token")
    print("=" * 70)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    request_payload = {
        "jsonrpc": "2.0",
        "id": "m2m-test-list",
        "method": "tools/list",
        "params": {},
    }

    print("\nRequest:")
    print(f"POST {gateway_endpoint}")
    print(f"Authorization: Bearer {access_token[:20]}...")

    try:
        response = requests.post(
            gateway_endpoint, headers=headers, json=request_payload, timeout=30
        )

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                print(f"\n✅ SUCCESS - M2M authentication validated")
                print(f"   Found {len(tools)} tool(s):")
                for tool in tools:
                    print(f"   • {tool['name']}")
                return True
            else:
                print("\n⚠️  Unexpected response format")
                print(json.dumps(result, indent=2))
                return False
        elif response.status_code == 403:
            print(f"\n❌ FAILED - Token rejected (403 Forbidden)")
            print("   Check:")
            print("   1. M2M client ID in Gateway's allowedClients")
            print("   2. Token endpoint and scope are correct")
            print("   3. Gateway deployed with OAuth enabled")
            return False
        elif response.status_code == 401:
            print(f"\n❌ FAILED - Unauthorized (401)")
            print("   Token may be invalid or expired")
            return False
        else:
            print(f"\n❌ FAILED - HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return False


def test_calculate_budget(gateway_endpoint, tool_name, access_token):
    """Test calculate_budget tool with M2M authentication"""
    print("\n" + "=" * 70)
    print("Step 3: Test tools/call with M2M Token")
    print("=" * 70)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    request_payload = {
        "jsonrpc": "2.0",
        "id": "m2m-test-calc",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": {"monthly_income": 7000}},
    }

    print("\nRequest:")
    print(f"POST {gateway_endpoint}")
    print(f"Tool: {tool_name}")
    print(f"Authorization: Bearer {access_token[:20]}...")

    try:
        response = requests.post(
            gateway_endpoint, headers=headers, json=request_payload, timeout=30
        )

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                print("\n✅ SUCCESS - Tool executed with M2M token")
                print("\nTool Output:")
                print("-" * 70)
                for item in content:
                    if item["type"] == "text":
                        print(item["text"])
                print("-" * 70)
                return True
            else:
                print("\n⚠️  Unexpected response format")
                print(json.dumps(result, indent=2))
                return False
        else:
            print(f"\n❌ FAILED - HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return False


def main():
    """Run M2M authentication tests"""
    print("=" * 70)
    print("M2M Authentication Testing")
    print("=" * 70)

    # Load configurations
    m2m_config = load_m2m_config()
    gateway_outputs = load_gateway_outputs()

    if not gateway_outputs.get("cognito_configured"):
        print("\n❌ Gateway not configured with OAuth")
        print("   Redeploy Gateway: python deploy.py")
        sys.exit(1)

    gateway_endpoint = gateway_outputs["gateway_endpoint"]
    tool_name = gateway_outputs["tool_name"]

    print(f"\nGateway Endpoint: {gateway_endpoint}")
    print(f"Tool Name: {tool_name}")
    print(f"OAuth Enabled: ✅")

    # Get M2M access token
    access_token = get_m2m_access_token(m2m_config)

    # Run tests
    results = []
    results.append(test_tools_list(gateway_endpoint, access_token))
    results.append(test_calculate_budget(gateway_endpoint, tool_name, access_token))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    total = len(results)
    passed = sum(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ M2M authentication working correctly!")
        print("\n🎉 Gateway is ready for agent integration")
        print("\nNext steps:")
        print("1. Update finance-personal-assistant agent code to use M2M pattern")
        print("2. See: agentcore-gateway/gateway-specs/agent_m2m_example.py")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        print("\nTroubleshooting:")
        print("1. Check Gateway deployment: python deploy.py")
        print("2. Verify M2M client in Cognito console")
        print("3. Review CloudWatch logs for Gateway")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        sys.exit(1)
