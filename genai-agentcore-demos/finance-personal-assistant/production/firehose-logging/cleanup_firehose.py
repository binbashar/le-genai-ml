#!/usr/bin/env python3
"""
Cleanup Firehose logging resources for Finance Personal Assistant.

Removes:
- Subscription filter
- Firehose delivery stream
- Lambda transformation function
- IAM roles (Lambda and Firehose)
- S3 bucket (and all logs)
"""

import boto3
from pathlib import Path
import yaml


def load_agent_config():
    """Load agent configuration from .bedrock_agentcore.yaml"""
    config_path = Path(__file__).parent.parent / ".bedrock_agentcore.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Agent config not found at {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    agent_name = config["default_agent"]
    agent_config = config["agents"][agent_name]

    return {
        "agent_name": agent_name,
        "agent_id": agent_config["bedrock_agentcore"]["agent_id"],
        "region": agent_config["aws"]["region"],
        "account": agent_config["aws"]["account"],
    }


def delete_subscription_filter(logs_client, log_group_name, filter_name):
    """Delete subscription filter"""
    print(f"🗑️  Deleting subscription filter: {filter_name}")
    try:
        logs_client.delete_subscription_filter(
            logGroupName=log_group_name, filterName=filter_name
        )
        print(f"   ✅ Subscription filter deleted")
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"   ℹ️  Subscription filter not found")


def delete_firehose_stream(firehose_client, stream_name):
    """Delete Firehose delivery stream"""
    print(f"🗑️  Deleting Firehose stream: {stream_name}")
    try:
        firehose_client.delete_delivery_stream(
            DeliveryStreamName=stream_name, AllowForceDelete=True
        )
        print(f"   ✅ Firehose stream deleted")
    except firehose_client.exceptions.ResourceNotFoundException:
        print(f"   ℹ️  Firehose stream not found")


def delete_lambda_function(lambda_client, function_name):
    """Delete Lambda function"""
    print(f"🗑️  Deleting Lambda function: {function_name}")
    try:
        lambda_client.delete_function(FunctionName=function_name)
        print(f"   ✅ Lambda function deleted")
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"   ℹ️  Lambda function not found")


def delete_iam_role(iam_client, role_name):
    """Delete IAM role and all inline and managed policies"""
    print(f"🗑️  Deleting IAM role: {role_name}")
    try:
        # Delete inline policies first
        policies = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in policies["PolicyNames"]:
            iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

        # Detach managed policies
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies["AttachedPolicies"]:
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy["PolicyArn"])

        # Delete role
        iam_client.delete_role(RoleName=role_name)
        print(f"   ✅ IAM role deleted")
    except iam_client.exceptions.NoSuchEntityException:
        print(f"   ℹ️  IAM role not found")


def delete_s3_bucket(s3_client, bucket_name):
    """Delete S3 bucket and all objects"""
    print(f"🗑️  Deleting S3 bucket: {bucket_name}")
    try:
        # Delete all objects first
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            if "Contents" in page:
                objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})

        # Delete bucket
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"   ✅ S3 bucket deleted (all logs removed)")
    except s3_client.exceptions.NoSuchBucket:
        print(f"   ℹ️  S3 bucket not found")


def main():
    print("=" * 60)
    print("Finance Personal Assistant - Firehose Cleanup")
    print("=" * 60)
    print()

    # Load agent configuration
    try:
        config = load_agent_config()
        print(f"📋 Agent Configuration:")
        print(f"   Agent Name: {config['agent_name']}")
        print(f"   Agent ID: {config['agent_id']}")
        print(f"   Region: {config['region']}")
        print()
    except Exception as e:
        print(f"❌ Failed to load agent configuration: {e}")
        return 1

    # Initialize AWS clients
    region = config["region"]
    account = config["account"]

    s3_client = boto3.client("s3", region_name=region)
    iam_client = boto3.client("iam", region_name=region)
    lambda_client = boto3.client("lambda", region_name=region)
    firehose_client = boto3.client("firehose", region_name=region)
    logs_client = boto3.client("logs", region_name=region)

    # Resource names
    agent_name = config["agent_name"]
    # Replace underscores with hyphens for S3 bucket name (S3 doesn't allow underscores)
    agent_name_safe = agent_name.replace("_", "-")
    bucket_name = f"{agent_name_safe}-logs-{account}-{region}"
    lambda_function_name = f"{agent_name}-log-transformer"
    lambda_role_name = f"{agent_name}-lambda-role"
    firehose_role_name = f"{agent_name}-firehose-role"
    subscription_role_name = f"{agent_name}-logs-to-firehose-role"
    stream_name = f"{agent_name}-logs"
    # Log group includes agent ID and endpoint name (DEFAULT)
    log_group_name = f"/aws/bedrock-agentcore/runtimes/{config['agent_id']}-DEFAULT"
    filter_name = f"{agent_name}-to-firehose"

    try:
        # Delete in reverse order of creation
        delete_subscription_filter(logs_client, log_group_name, filter_name)
        print()

        delete_firehose_stream(firehose_client, stream_name)
        print()

        delete_iam_role(iam_client, subscription_role_name)
        print()

        delete_iam_role(iam_client, firehose_role_name)
        print()

        delete_lambda_function(lambda_client, lambda_function_name)
        print()

        delete_iam_role(iam_client, lambda_role_name)
        print()

        delete_s3_bucket(s3_client, bucket_name)
        print()

        print("=" * 60)
        print("✅ Cleanup Complete!")
        print("=" * 60)
        print()
        print("⚠️  Note: CloudWatch log group was NOT deleted")
        print(f"   ({log_group_name})")
        print("   This is managed by AgentCore Runtime.")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
