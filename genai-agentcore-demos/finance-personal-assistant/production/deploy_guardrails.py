#!/usr/bin/env python3
"""
Deploy gambling guardrails to AWS Bedrock.

This script creates or updates the gambling guardrail with AWS best practices:
- Content policy filters for harmful content
- Word policy for gambling-related terms
- PII protection with automatic redaction (ANONYMIZE/BLOCK)
- Contextual grounding for hallucination prevention

Usage:
    # Deploy guardrail (create if doesn't exist)
    python deploy_guardrails.py

    # Deploy and create production version
    python deploy_guardrails.py --create-version

    # Verify guardrail only (no creation)
    python deploy_guardrails.py --verify-only
"""

import argparse
import json
import sys
from datetime import datetime

import boto3
from config import get_region
from utils.guardrail import (
    create_gambling_guardrail,
    create_guardrail_version,
    get_gambling_guardrail_id,
    delete_gambling_guardrail,
)


def publish_guardrail_to_ssm(guardrail_id: str, version: str = "DRAFT"):
    """
    Publish guardrail configuration to SSM Parameter Store for service discovery.

    Follows the same pattern as agent ARN publishing in launch.sh.
    This allows config.py to discover the guardrail dynamically at runtime.

    Args:
        guardrail_id: The guardrail ID to publish
        version: The guardrail version (default: "DRAFT")
    """
    ssm = boto3.client("ssm", region_name=get_region())

    config = {
        "guardrail_id": guardrail_id,
        "version": version,
        "updated_at": datetime.now().isoformat(),
    }

    parameter_name = "/agentcore/finance-personal-assistant/guardrail-config"

    try:
        ssm.put_parameter(
            Name=parameter_name,
            Value=json.dumps(config),
            Type="String",
            Description="Guardrail configuration for Finance Personal Assistant",
            Overwrite=True,
        )
        print(f"✅ Published guardrail config to SSM: {parameter_name}")
    except Exception as e:
        print(f"⚠️  Failed to publish to SSM: {e}")
        print("   Agent will still work but must use direct API lookup")


def deploy_guardrails(create_version: bool = False, verify_only: bool = False):
    """
    Deploy gambling guardrails to AWS Bedrock.

    Args:
        create_version: If True, create an immutable production version after deployment
        verify_only: If True, only verify existing guardrail (don't create)

    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    print("=" * 70)
    print("AWS Bedrock Guardrails Deployment")
    print("=" * 70)
    print()

    # Check if guardrail already exists
    print("🔍 Checking for existing gambling guardrail...")
    existing_id = get_gambling_guardrail_id()

    if existing_id:
        print(f"✅ Guardrail already exists with ID: {existing_id}")
        print()

        if verify_only:
            print("✓ Verification complete - guardrail is active")
            return 0

        # Ask if user wants to recreate (in verify_only mode, we skip this)
        print("Guardrail configuration:")
        print(
            "  • Content filters: SEXUAL, VIOLENCE, HATE, INSULTS, MISCONDUCT, PROMPT_ATTACK"
        )
        print("  • Word policy: 19 gambling terms + PROFANITY")
        print(
            "  • PII protection: EMAIL, PHONE, NAME (ANONYMIZE); SSN, CREDIT_DEBIT_CARD (BLOCK)"
        )
        print("  • Contextual grounding: GROUNDING, RELEVANCE (threshold: 0.7)")
        print()
        print("Note: Guardrail already exists. To update, delete it first using:")
        print(
            "  uv run python -c 'from utils.guardrail import delete_gambling_guardrail; delete_gambling_guardrail()'"
        )
        print()

        guardrail_id = existing_id

    else:
        if verify_only:
            print("❌ Guardrail does not exist")
            print()
            print("Run without --verify-only to create it:")
            print("  python deploy_guardrails.py")
            return 1

        # Create new guardrail
        print("📝 Creating new gambling guardrail with AWS best practices...")
        print()

        try:
            guardrail_id, guardrail_arn = create_gambling_guardrail()
            print()
            print("✅ Guardrail created successfully!")
            print(f"   ID:  {guardrail_id}")
            print(f"   ARN: {guardrail_arn}")
            print()
        except Exception as e:
            print(f"❌ Failed to create guardrail: {e}")
            return 1

    # Create production version if requested
    if create_version and not verify_only:
        print("📦 Creating production version...")
        print()

        try:
            version = create_guardrail_version(guardrail_id)
            if version:
                print()
                print(f"✅ Production version created: {version}")
                print()
                print("To use this version in production, update config.py:")
                print(f'  guardrail_version="{version}"  # Instead of "DRAFT"')
                print()
            else:
                print("⚠️ Failed to create production version")
                print("   You can still use DRAFT version for testing")
                print()
        except Exception as e:
            print(f"⚠️ Version creation failed: {e}")
            print("   You can still use DRAFT version for testing")
            print()

    # Publish guardrail configuration to SSM (service discovery pattern)
    if not verify_only:
        print("📡 Publishing guardrail config to SSM Parameter Store...")
        print()
        guardrail_version = version if (create_version and version) else "DRAFT"
        publish_guardrail_to_ssm(guardrail_id, guardrail_version)
        print()

    # Summary
    print("=" * 70)
    print("Deployment Summary")
    print("=" * 70)
    print(f"Guardrail ID: {guardrail_id}")
    print(
        f"Version:      {'DRAFT' if not create_version else version if version else 'DRAFT'}"
    )
    print()
    print("Next steps:")
    print("  1. Agent will automatically use this guardrail (via config.py)")
    print("  2. Deploy agent: ./configure.sh && ./launch.sh")
    print("  3. Test guardrail:")
    print("     python test_gambling_guardrail.py")
    print()
    print("Guardrail capabilities:")
    print("  ✓ Blocks gambling-related content (casino, betting, poker, etc.)")
    print("  ✓ Redacts PII automatically (email, phone, SSN, credit cards)")
    print("  ✓ Prevents hallucinations (contextual grounding)")
    print("  ✓ Filters harmful content (sexual, violence, hate, insults)")
    print("  ✓ Silent redaction (conversation history protected)")
    print()

    return 0


def delete_guardrails(guardrail_id: str = None):
    """
    Delete gambling guardrail from AWS Bedrock.
    """
    print("=" * 70)
    print("Deleting gambling guardrail...")
    print("=" * 70)
    print()
    delete_gambling_guardrail(guardrail_id)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Deploy AWS Bedrock Guardrails for Finance Personal Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy guardrail (create if doesn't exist)
  python deploy_guardrails.py

  # Deploy and create production version
  python deploy_guardrails.py --create-version

  # Verify guardrail exists without creating
  python deploy_guardrails.py --verify-only

Environment:
  AWS_PROFILE - AWS profile to use (default: from boto3 config)
  AWS_REGION  - AWS region (default: us-west-2)
        """,
    )

    parser.add_argument(
        "--create-version",
        action="store_true",
        help="Create an immutable production version after deployment (recommended for prod)",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing guardrail (don't create new one)",
    )

    parser.add_argument(
        "--delete-guardrail",
        action="store_true",
        help="Delete existing guardrail",
    )

    args = parser.parse_args()

    # Run deployment
    exit_code = deploy_guardrails(
        create_version=args.create_version,
        verify_only=args.verify_only,
    )

    if args.delete_guardrail:
        exit_code = delete_guardrails(guardrail_id=args.delete_guardrail)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
