"""
Workshop utilities for Jupyter notebooks.

This module provides simplified versions of production utilities
specifically designed for the workshop learning experience.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError


def create_guardrail() -> Tuple[str, str]:
    """
    Create a Bedrock guardrail for the workshop.

    Returns:
        Tuple of (guardrail_id, guardrail_arn)
    """
    bedrock = boto3.client("bedrock", region_name="us-west-2")

    guardrail_name = "guardrail-no-gambling-advice"

    # Check if guardrail already exists
    try:
        response = bedrock.list_guardrails()
        for guardrail in response.get("guardrails", []):
            if guardrail["name"] == guardrail_name:
                print(f"Using existing guardrail: {guardrail_name}")
                return guardrail["id"], guardrail["arn"]
    except Exception as e:
        print(f"Warning: Could not list guardrails: {e}")

    # Create new guardrail
    print(f"Creating new guardrail '{guardrail_name}'...")

    try:
        response = bedrock.create_guardrail(
            name=guardrail_name,
            description="Workshop guardrail - blocks gambling-related content",
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"}
                ]
            },
            wordPolicyConfig={
                "wordsConfig": [
                    # Gambling activities
                    {"text": "gambling"},
                    {"text": "casino"},
                    {"text": "betting"},
                    {"text": "poker"},
                    {"text": "blackjack"},
                    {"text": "roulette"},
                    {"text": "slot machine"},
                    {"text": "sports betting"},
                    {"text": "online gambling"},
                    {"text": "gaming tables"},
                    # Gambling advice
                    {"text": "gambling strategy"},
                    {"text": "betting tips"},
                    {"text": "casino advice"},
                    {"text": "poker strategy"},
                    {"text": "how to gamble"},
                    {"text": "gambling recommendations"},
                    # Gambling-related financial terms
                    {"text": "gambling winnings"},
                    {"text": "betting odds"},
                    {"text": "casino stocks"},
                    {"text": "gambling investment"},
                ],
                "managedWordListsConfig": [{"type": "PROFANITY"}]
            },
            blockedInputMessaging="I apologize, but I'm not able to provide advice or information about that topic. As a financial advisor, I can help with budgeting, investing, savings, and other responsible financial planning topics. How can I assist you with your financial goals?",
            blockedOutputsMessaging="I apologize, but I cannot provide information related to that topic. For your safety and responsible financial management, please ask about other financial topics such as budgeting, investing, or savings strategies."
        )

        guardrail_id = response["guardrailId"]
        guardrail_arn = response["guardrailArn"]

        print(f"✅ Guardrail created successfully")
        print(f"   ID: {guardrail_id}")
        print(f"   ARN: {guardrail_arn}")

        return guardrail_id, guardrail_arn

    except Exception as e:
        print(f"❌ Error creating guardrail: {e}")
        raise


def delete_guardrail() -> None:
    """Delete the workshop guardrail."""
    bedrock = boto3.client("bedrock", region_name="us-west-2")

    guardrail_name = "guardrail-no-gambling-advice"

    try:
        # Find the guardrail
        response = bedrock.list_guardrails()
        for guardrail in response.get("guardrails", []):
            if guardrail["name"] == guardrail_name:
                print(f"Deleting guardrail: {guardrail_name}")
                bedrock.delete_guardrail(guardrailIdentifier=guardrail["id"])
                print("✅ Guardrail deleted successfully")
                return

        print(f"ℹ️  Guardrail '{guardrail_name}' not found")

    except Exception as e:
        print(f"❌ Error deleting guardrail: {e}")
        raise


def setup_cognito_user_pool() -> Dict[str, str]:
    """
    Create a Cognito User Pool for workshop authentication.

    Returns:
        Dictionary with user_pool_id, client_id, discovery_url, and bearer_token
    """
    cognito = boto3.client("cognito-idp", region_name="us-west-2")

    pool_name = "workshop-agent-pool"

    try:
        # Create user pool
        print(f"Creating Cognito User Pool: {pool_name}")
        pool_response = cognito.create_user_pool(
            PoolName=pool_name,
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": False,
                    "RequireLowercase": False,
                    "RequireNumbers": False,
                    "RequireSymbols": False
                }
            },
            AutoVerifiedAttributes=["email"],
            UsernameAttributes=["email"]
        )

        pool_id = pool_response["UserPool"]["Id"]
        print(f"Pool id: {pool_id}")

        # Create app client
        client_response = cognito.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName="workshop-client",
            ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
        )

        client_id = client_response["UserPoolClient"]["ClientId"]
        print(f"Client ID: {client_id}")

        # Create test user
        username = "testuser"
        password = "TestPass123!"

        try:
            cognito.admin_create_user(
                UserPoolId=pool_id,
                Username=username,
                TemporaryPassword=password,
                MessageAction="SUPPRESS"
            )

            # Set permanent password
            cognito.admin_set_user_password(
                UserPoolId=pool_id,
                Username=username,
                Password=password,
                Permanent=True
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "UsernameExistsException":
                raise

        # Get bearer token
        auth_response = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            ClientId=client_id,
            AuthParameters={"USERNAME": username, "PASSWORD": password}
        )

        bearer_token = auth_response["AuthenticationResult"]["AccessToken"]

        # Get region
        region = boto3.Session().region_name or "us-west-2"
        discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

        print(f"Discovery URL: {discovery_url}")
        print(f"Bearer Token: {bearer_token}")

        return {
            "user_pool_id": pool_id,
            "client_id": client_id,
            "discovery_url": discovery_url,
            "bearer_token": bearer_token
        }

    except Exception as e:
        print(f"❌ Error setting up Cognito: {e}")
        raise


def delete_cognito_user_pool() -> None:
    """Delete the workshop Cognito User Pool."""
    cognito = boto3.client("cognito-idp", region_name="us-west-2")

    pool_name = "workshop-agent-pool"

    try:
        # List all user pools
        response = cognito.list_user_pools(MaxResults=50)

        for pool in response.get("UserPools", []):
            if pool["Name"] == pool_name:
                pool_id = pool["Id"]
                print(f"Deleting Cognito User Pool: {pool_name} ({pool_id})")
                cognito.delete_user_pool(UserPoolId=pool_id)
                print("✅ User Pool deleted successfully")
                return

        print(f"ℹ️  User Pool '{pool_name}' not found")

    except Exception as e:
        print(f"❌ Error deleting user pool: {e}")
        raise


def reauthenticate_user(client_id: str, username: str = "testuser", password: str = "TestPass123!") -> str:
    """
    Get a fresh bearer token for API calls.

    Args:
        client_id: Cognito app client ID
        username: Username to authenticate
        password: User password

    Returns:
        Bearer token (access token)
    """
    cognito = boto3.client("cognito-idp", region_name="us-west-2")

    try:
        response = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            ClientId=client_id,
            AuthParameters={"USERNAME": username, "PASSWORD": password}
        )

        return response["AuthenticationResult"]["AccessToken"]

    except Exception as e:
        print(f"❌ Error authenticating: {e}")
        raise


def pretty_print_messages(messages: list) -> None:
    """
    Pretty print conversation messages for the workshop.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
    """
    print("\n" + "=" * 80)
    print(f"💬 CONVERSATION HISTORY ({len(messages)} messages)")
    print("=" * 80 + "\n")

    user_count = 0
    assistant_count = 0

    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            user_count += 1
            icon = "👤"
            label = f"MESSAGE {i} (USER)"
        elif role == "assistant":
            assistant_count += 1
            icon = "🤖"
            label = f"MESSAGE {i} (ASSISTANT)"
        else:
            icon = "❓"
            label = f"MESSAGE {i} ({role.upper()})"

        print(f"{icon} {label}:")
        print("-" * 40)

        # Truncate very long messages
        if len(content) > 500:
            content = content[:500] + "\n  ... [content truncated]"

        # Indent content
        for line in content.split("\n"):
            print(f"  {line}")

        print()

    print("=" * 80)
    print(f"📊 SUMMARY: {len(messages)} total messages")
    print(f"   • User: {user_count} messages")
    print(f"   • Assistant: {assistant_count} messages")
    print()


def get_guardrail_id() -> Optional[str]:
    """
    Get the workshop guardrail ID if it exists.

    Returns:
        Guardrail ID or None if not found
    """
    bedrock = boto3.client("bedrock", region_name="us-west-2")

    try:
        response = bedrock.list_guardrails()
        for guardrail in response.get("guardrails", []):
            if guardrail["name"] == "guardrail-no-gambling-advice":
                return guardrail["id"]
    except Exception:
        pass

    return None
