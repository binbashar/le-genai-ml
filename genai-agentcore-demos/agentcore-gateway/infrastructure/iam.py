"""
IAM roles and policies for Gateway infrastructure.

This module creates:
1. Lambda execution role (for tool functions)
2. Gateway service role (for invoking Lambda functions)

Following AWS best practices for least privilege access.
"""

import json
import logging

logger = logging.getLogger(__name__)


def create_lambda_execution_role(
    iam_client,
    role_name: str,
    account_id: str,
    region: str,
    description: str,
    tags: list,
) -> str:
    """
    Create IAM role for Lambda execution.

    This role allows Lambda functions to:
    - Write logs to CloudWatch Logs
    - (Future) Access other AWS services as needed

    Args:
        iam_client: Boto3 IAM client
        role_name: Name for the execution role
        account_id: AWS account ID
        region: AWS region
        description: Role description
        tags: Resource tags

    Returns:
        ARN of the created or existing role
    """
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

    # Create role
    try:
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
            Tags=tags,
        )
        role_arn = response["Role"]["Arn"]
        logger.info(f"✓ Created Lambda execution role: {role_arn}")

    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        logger.info(f"✓ Lambda execution role already exists: {role_arn}")

    # Attach managed policy for CloudWatch Logs
    try:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        logger.info("  ✓ Attached AWSLambdaBasicExecutionRole policy")
    except Exception as e:
        # Policy may already be attached
        logger.debug(f"Policy attachment: {e}")

    return role_arn


def create_gateway_service_role(
    iam_client,
    role_name: str,
    account_id: str,
    region: str,
    description: str,
    tags: list,
) -> str:
    """
    Create IAM role for Gateway service.

    This role allows AgentCore Gateway to:
    - Invoke Lambda functions prefixed with 'agentcore-gateway-'

    Args:
        iam_client: Boto3 IAM client
        role_name: Name for the service role
        account_id: AWS account ID
        region: AWS region
        description: Role description
        tags: Resource tags

    Returns:
        ARN of the created or existing role
    """
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GatewayAssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/*"
                    },
                },
            }
        ],
    }

    # Create role
    try:
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
            Tags=tags,
        )
        role_arn = response["Role"]["Arn"]
        logger.info(f"✓ Created Gateway service role: {role_arn}")

    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        logger.info(f"✓ Gateway service role already exists: {role_arn}")

    # Inline policy for Lambda invocation
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": f"arn:aws:lambda:{region}:{account_id}:function:agentcore-gateway-*",
            }
        ],
    }

    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="LambdaInvokePolicy",
            PolicyDocument=json.dumps(policy_document),
        )
        logger.info("  ✓ Attached Lambda invoke policy")
    except Exception as e:
        logger.debug(f"Policy attachment: {e}")

    return role_arn


def delete_iam_roles(iam_client, lambda_role_name: str, gateway_role_name: str):
    """
    Delete IAM roles created for Gateway infrastructure.

    Args:
        iam_client: Boto3 IAM client
        lambda_role_name: Lambda execution role name
        gateway_role_name: Gateway service role name
    """
    for role_name in [lambda_role_name, gateway_role_name]:
        try:
            # Detach managed policies
            policies = iam_client.list_attached_role_policies(RoleName=role_name)
            for policy in policies["AttachedPolicies"]:
                iam_client.detach_role_policy(
                    RoleName=role_name, PolicyArn=policy["PolicyArn"]
                )

            # Delete inline policies
            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            for policy_name in inline_policies["PolicyNames"]:
                iam_client.delete_role_policy(
                    RoleName=role_name, PolicyName=policy_name
                )

            # Delete role
            iam_client.delete_role(RoleName=role_name)
            logger.info(f"✓ Deleted IAM role: {role_name}")

        except iam_client.exceptions.NoSuchEntityException:
            logger.info(f"  IAM role does not exist: {role_name}")
        except Exception as e:
            logger.error(f"Failed to delete IAM role {role_name}: {e}")
