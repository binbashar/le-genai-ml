"""
Post-deployment script for Cognito user setup.

Automatically invoked by deploy.sh after CDK stack deployment.
Sets permanent passwords for demo users created in the stack.
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

    # Read CDK outputs
    outputs_file = script_dir / "outputs.json"
    if not outputs_file.exists():
        print("❌ Error: outputs.json not found. CDK deployment may have failed.")
        sys.exit(1)

    with open(outputs_file) as f:
        stack_outputs = list(json.load(f).values())[0]

    user_pool_id = stack_outputs["UserPoolId"]
    region = stack_outputs["Region"]

    print("📋 Cognito Configuration:")
    print(f"   User Pool ID: {user_pool_id}")
    print(f"   Region: {region}")

    # Read demo users
    demo_users_file = script_dir.parent.parent / ".demo_users.json"
    if not demo_users_file.exists():
        print(
            "\n⚠️  Warning: .demo_users.json not found. Skipping password setup."
        )
        print("   To create demo users with passwords, copy .demo_users.json.example")
        return

    with open(demo_users_file) as f:
        users = json.load(f)

    # Validate user data
    for user in users:
        if "username" not in user or "password" not in user:
            print(f"❌ Error: User missing 'username' or 'password' field: {user}")
            sys.exit(1)

    # Set permanent passwords
    set_permanent_passwords(user_pool_id, region, users)

    print("\n✅ Post-deployment setup complete!")
    print("\n📝 Users are ready for authentication:")
    for user in users:
        print(f"   - {user['username']} (password set)")


if __name__ == "__main__":
    main()
