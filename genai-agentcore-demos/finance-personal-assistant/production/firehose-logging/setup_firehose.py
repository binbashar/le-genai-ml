#!/usr/bin/env python3
"""
Setup Firehose logging for Finance Personal Assistant AgentCore logs.

This script creates:
1. S3 bucket for log storage
2. Lambda transformation function (converts logs to Bedrock evaluation format)
3. IAM role for Lambda execution
4. IAM role for Firehose to write to S3 and invoke Lambda
5. Firehose delivery stream with Lambda processor
6. IAM role for CloudWatch Logs to write to Firehose
7. Subscription filter on the AgentCore log group

No CDK/CloudFormation - uses boto3 directly for simplicity.
"""

import json
import time
import boto3
from pathlib import Path
import yaml
import zipfile
import io


def load_agent_config():
    """Load agent configuration from .bedrock_agentcore.yaml"""
    config_path = Path(__file__).parent.parent / ".bedrock_agentcore.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Agent config not found at {config_path}. "
            "Please deploy the agent first using ./launch.sh"
        )

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


def create_s3_bucket(s3_client, bucket_name, region):
    """Create S3 bucket for log storage"""
    print(f"📦 Creating S3 bucket: {bucket_name}")

    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )

        # Enable default encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            },
        )

        print(f"   ✅ Bucket created: {bucket_name}")
        return bucket_name

    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        print(f"   ℹ️  Bucket already exists: {bucket_name}")
        return bucket_name


def create_lambda_function(lambda_client, iam_client, function_name, role_name, account, region):
    """Create Lambda transformation function"""
    print(f"λ Creating Lambda transformation function: {function_name}")

    # Create Lambda execution role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Allows Lambda to transform firehose logs",
        )
        lambda_role_arn = role["Role"]["Arn"]
        print(f"   ✅ Lambda role created: {lambda_role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role = iam_client.get_role(RoleName=role_name)
        lambda_role_arn = role["Role"]["Arn"]
        print(f"   ℹ️  Lambda role already exists: {lambda_role_arn}")

    # Attach CloudWatch Logs policy
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

    print("   ⏳ Waiting for Lambda role to propagate...")
    time.sleep(10)

    # Read and package Lambda function code
    lambda_code_path = Path(__file__).parent / "lambda_transform.py"
    if not lambda_code_path.exists():
        raise FileNotFoundError(f"Lambda code not found at {lambda_code_path}")

    # Create ZIP archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(lambda_code_path, "lambda_transform.py")
    zip_buffer.seek(0)

    # Create or update Lambda function
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.13",
            Role=lambda_role_arn,
            Handler="lambda_transform.lambda_handler",
            Code={"ZipFile": zip_buffer.read()},
            Description="Transforms AgentCore logs to Bedrock evaluation format",
            Timeout=300,
            MemorySize=512,
        )
        function_arn = response["FunctionArn"]
        print(f"   ✅ Lambda function created: {function_arn}")
    except lambda_client.exceptions.ResourceConflictException:
        # Function exists, update it
        zip_buffer.seek(0)
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_buffer.read(),
        )
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response["Configuration"]["FunctionArn"]
        print(f"   ℹ️  Lambda function already exists, code updated: {function_arn}")

    return function_arn, lambda_role_arn


def create_firehose_role(iam_client, role_name, bucket_name, lambda_arn, account, region):
    """Create IAM role for Firehose to write to S3 and invoke Lambda"""
    print(f"🔐 Creating IAM role for Firehose: {role_name}")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "firehose.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Allows Firehose to write finance assistant logs to S3 and invoke Lambda",
        )
        role_arn = role["Role"]["Arn"]
        print(f"   ✅ Role created: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
        print(f"   ℹ️  Role already exists: {role_arn}")

    # Attach inline policy for S3 and Lambda access
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:AbortMultipartUpload",
                    "s3:GetBucketLocation",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                    "s3:PutObject",
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction",
                    "lambda:GetFunctionConfiguration",
                ],
                "Resource": lambda_arn,
            },
        ],
    }

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="S3AndLambdaAccess",
        PolicyDocument=json.dumps(policy_document),
    )

    print(f"   ✅ S3 and Lambda policy attached")

    # Wait for role to propagate
    print("   ⏳ Waiting for IAM role to propagate...")
    time.sleep(10)

    return role_arn


def create_firehose_stream(
    firehose_client, stream_name, bucket_name, role_arn, lambda_arn
):
    """Create Firehose delivery stream with Lambda processor"""
    print(f"🚀 Creating Firehose delivery stream: {stream_name}")

    try:
        response = firehose_client.create_delivery_stream(
            DeliveryStreamName=stream_name,
            DeliveryStreamType="DirectPut",
            ExtendedS3DestinationConfiguration={
                "RoleARN": role_arn,
                "BucketARN": f"arn:aws:s3:::{bucket_name}",
                "Prefix": "evaluation-data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
                "ErrorOutputPrefix": "errors/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/!{firehose:error-output-type}",
                "BufferingHints": {
                    "SizeInMBs": 5,
                    "IntervalInSeconds": 60,
                },
                # UNCOMPRESSED for JSONL readability
                "CompressionFormat": "UNCOMPRESSED",
                # Lambda transformation
                "ProcessingConfiguration": {
                    "Enabled": True,
                    "Processors": [
                        {
                            "Type": "Lambda",
                            "Parameters": [
                                {
                                    "ParameterName": "LambdaArn",
                                    "ParameterValue": lambda_arn,
                                },
                                {
                                    "ParameterName": "BufferSizeInMBs",
                                    "ParameterValue": "3",
                                },
                                {
                                    "ParameterName": "BufferIntervalInSeconds",
                                    "ParameterValue": "60",
                                },
                            ],
                        }
                    ],
                },
            },
        )

        stream_arn = response["DeliveryStreamARN"]
        print(f"   ✅ Stream created: {stream_arn}")

        # Wait for stream to become active (poll manually since waiter doesn't exist)
        print("   ⏳ Waiting for stream to become active...")
        max_attempts = 30
        for attempt in range(max_attempts):
            response = firehose_client.describe_delivery_stream(DeliveryStreamName=stream_name)
            status = response["DeliveryStreamDescription"]["DeliveryStreamStatus"]
            if status == "ACTIVE":
                print("   ✅ Stream is active")
                break
            elif status in ["CREATING", "UPDATING"]:
                time.sleep(2)
            else:
                raise Exception(f"Unexpected stream status: {status}")
        else:
            raise Exception(f"Stream did not become active after {max_attempts * 2} seconds")

        return stream_arn

    except firehose_client.exceptions.ResourceInUseException:
        response = firehose_client.describe_delivery_stream(
            DeliveryStreamName=stream_name
        )
        stream_arn = response["DeliveryStreamDescription"]["DeliveryStreamARN"]
        print(f"   ℹ️  Stream already exists: {stream_arn}")
        return stream_arn


def create_subscription_role(iam_client, role_name, stream_arn, account, region):
    """Create IAM role for CloudWatch Logs to write to Firehose"""
    print(f"🔐 Creating IAM role for CloudWatch Logs: {role_name}")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "logs.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringLike": {
                        "aws:SourceArn": f"arn:aws:logs:{region}:{account}:*"
                    }
                },
            }
        ],
    }

    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Allows CloudWatch Logs to send finance assistant logs to Firehose",
        )
        role_arn = role["Role"]["Arn"]
        print(f"   ✅ Role created: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
        print(f"   ℹ️  Role already exists: {role_arn}")

    # Attach inline policy for Firehose access
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["firehose:PutRecord", "firehose:PutRecordBatch"],
                "Resource": stream_arn,
            }
        ],
    }

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="FirehosePutAccess",
        PolicyDocument=json.dumps(policy_document),
    )

    print(f"   ✅ Firehose put policy attached")

    # Wait for role to propagate
    print("   ⏳ Waiting for IAM role to propagate...")
    time.sleep(10)

    return role_arn


def create_subscription_filter(
    logs_client, log_group_name, filter_name, stream_arn, role_arn
):
    """Create subscription filter on CloudWatch log group"""
    print(f"📡 Creating subscription filter: {filter_name}")

    try:
        logs_client.put_subscription_filter(
            logGroupName=log_group_name,
            filterName=filter_name,
            filterPattern="",  # Empty pattern = all logs
            destinationArn=stream_arn,
            roleArn=role_arn,
        )
        print(f"   ✅ Subscription filter created on {log_group_name}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"   ℹ️  Subscription filter already exists")


def main():
    print("=" * 60)
    print("Finance Personal Assistant - Firehose Logging Setup")
    print("=" * 60)
    print()

    # Load agent configuration
    try:
        config = load_agent_config()
        print(f"📋 Agent Configuration:")
        print(f"   Agent Name: {config['agent_name']}")
        print(f"   Agent ID: {config['agent_id']}")
        print(f"   Region: {config['region']}")
        print(f"   Account: {config['account']}")
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
        # 1. Create S3 bucket
        create_s3_bucket(s3_client, bucket_name, region)
        print()

        # 2. Create Lambda transformation function
        lambda_arn, lambda_role_arn = create_lambda_function(
            lambda_client, iam_client, lambda_function_name, lambda_role_name, account, region
        )
        print()

        # 3. Create Firehose IAM role
        firehose_role_arn = create_firehose_role(
            iam_client, firehose_role_name, bucket_name, lambda_arn, account, region
        )
        print()

        # 4. Create Firehose delivery stream with Lambda processor
        stream_arn = create_firehose_stream(
            firehose_client, stream_name, bucket_name, firehose_role_arn, lambda_arn
        )
        print()

        # 5. Create CloudWatch Logs IAM role
        subscription_role_arn = create_subscription_role(
            iam_client, subscription_role_name, stream_arn, account, region
        )
        print()

        # 6. Create subscription filter
        create_subscription_filter(
            logs_client, log_group_name, filter_name, stream_arn, subscription_role_arn
        )
        print()

        # Summary
        print("=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print()
        print("📊 Resources Created:")
        print(f"   S3 Bucket: {bucket_name}")
        print(f"   Lambda Function: {lambda_function_name}")
        print(f"   Firehose Stream: {stream_name}")
        print(f"   Log Group: {log_group_name}")
        print(f"   Subscription Filter: {filter_name}")
        print()
        print("🔍 Verification:")
        print(f"   1. Generate logs by invoking the agent:")
        print(f"      cd .. && ./health.sh")
        print()
        print(f"   2. Check Lambda logs (transformation function):")
        print(f"      aws logs tail /aws/lambda/{lambda_function_name} --follow")
        print()
        print(f"   3. Check S3 bucket (wait ~60 seconds for buffering):")
        print(f"      aws s3 ls s3://{bucket_name}/evaluation-data/ --recursive")
        print()
        print(f"   4. Download and view evaluation data (JSONL format):")
        print(f"      aws s3 cp s3://{bucket_name}/evaluation-data/year=2025/... - | head")
        print()
        print("📝 Next Steps:")
        print(f"   - Review transformed data in S3 bucket")
        print(f"   - Use evaluation data for Bedrock Model Evaluation")
        print(f"   - Create evaluation jobs with LLM-as-a-judge metrics")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
