"""
AWS Configuration Management
Centralized configuration for region and AWS service clients
"""

import os
from functools import lru_cache

import boto3

# Primary region configuration
DEFAULT_REGION = "us-west-2"


def get_region() -> str:
    """
    Get AWS region with standard precedence order:
    1. AWS_REGION environment variable
    2. AWS_DEFAULT_REGION environment variable
    3. boto3 session default (from ~/.aws/config)
    4. Hardcoded default (us-west-2)

    Returns:
        str: AWS region name
    """
    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or boto3.Session().region_name
        or DEFAULT_REGION
    )


@lru_cache(maxsize=1)
def get_boto3_session() -> boto3.Session:
    """
    Get or create a cached boto3 session.
    Reuses the same session across the application for efficiency.

    Returns:
        boto3.Session: Cached boto3 session with configured region
    """
    return boto3.Session(region_name=get_region())


def get_client(service_name: str, **kwargs):
    """
    Create AWS service client with configured region.

    Args:
        service_name: AWS service name (e.g., 'bedrock-agentcore', 'sts')
        **kwargs: Additional client configuration (e.g., config=Config(...))

    Returns:
        boto3.client: Configured boto3 client
    """
    session = get_boto3_session()
    return session.client(service_name, **kwargs)
