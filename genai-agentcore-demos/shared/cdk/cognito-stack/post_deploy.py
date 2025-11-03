"""
Post-deployment script for Cognito user setup.

Automatically invoked by deploy.sh after CDK stack deployment.
Sets permanent passwords for demo users created in the stack.

Note: Agent ARN publishing to SSM is handled by shared/post_agent_deploy.py
after AgentCore deployment (not during Cognito CDK deployment).
"""

import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def set_permanent_passwords(user_pool_id: str, region: str, users: list[dict]) -> None:
    """
    Set permanent passwords for Cognito users.

    Args:
        user_pool_id: Cognito user pool ID
        region: AWS region
        users: List of user dicts with username and password fields
    """
    cognito_client = boto3.client("cognito-idp", region_name=region)

    print("\n🔐 Setting permanent passwords for demo users...")

    for user in users:
        username = user["username"]
        password = user["password"]

        try:
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=username,
                Password=password,
                Permanent=True,
            )
            print(f"   ✅ Set password for user: {username}")

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "UserNotFoundException":
                print(f"   ⚠️  User not found: {username} (may not be created yet)")
            else:
                print(f"   ❌ Error setting password for {username}: {e}")
                raise


def main():
    """Main post-deployment setup."""
    script_dir = Path(__file__).parent

    # Read from SSM Parameter Store
    ssm_client = boto3.client("ssm")
    region = boto3.Session().region_name or "us-west-2"

    try:
        response = ssm_client.get_parameter(Name="/agentcore/shared/cognito-pool-id")
        user_pool_id = response["Parameter"]["Value"]
    except ClientError as e:
        print(f"❌ Error: Could not read Cognito Pool ID from SSM: {e}")
        print("   Make sure the CDK stack deployed successfully.")
        sys.exit(1)

    print("📋 Cognito Configuration:")
    print(f"   User Pool ID: {user_pool_id}")
    print(f"   Region: {region}")

    # Read demo users from same directory
    demo_users_file = script_dir / ".demo_users.json"
    if demo_users_file.exists():
        with open(demo_users_file) as f:
            users = json.load(f)

        # Validate user data
        for user in users:
            if "username" not in user or "password" not in user:
                print(f"❌ Error: User missing 'username' or 'password' field: {user}")
                sys.exit(1)

        # Set permanent passwords
        set_permanent_passwords(user_pool_id, region, users)

        print("\n📝 Users are ready for authentication:")
        for user in users:
            print(f"   - {user['username']} (password set)")
    else:
        print("\n⚠️  Warning: Demo users file not found. Skipping password setup.")
        print(f"   Expected location: {demo_users_file}")

    print("\n✅ Post-deployment setup complete!")
    print("\nℹ️  Note: Agent ARN will be published to SSM after running ./launch.sh")


if __name__ == "__main__":
    main()
