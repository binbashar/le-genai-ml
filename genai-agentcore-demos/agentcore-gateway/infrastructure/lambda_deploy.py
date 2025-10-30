"""
Lambda function deployment module.

Handles:
- Packaging Lambda code as ZIP
- Creating/updating Lambda functions
- Configuring function settings
"""

import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Dict


logger = logging.getLogger(__name__)


def package_lambda_code(tool_dir: Path) -> bytes:
    """
    Package Lambda function code as ZIP file.

    Args:
        tool_dir: Directory containing main.py

    Returns:
        ZIP file as bytes
    """
    main_py = tool_dir / "main.py"

    if not main_py.exists():
        raise FileNotFoundError(f"Lambda handler not found: {main_py}")

    # Create zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(main_py, "main.py")

    zip_buffer.seek(0)
    code_bytes = zip_buffer.read()

    logger.info(f"  Packaged Lambda code: {len(code_bytes)} bytes")
    return code_bytes


def deploy_lambda_function(
    lambda_client,
    function_name: str,
    role_arn: str,
    handler: str,
    runtime: str,
    memory: int,
    timeout: int,
    architecture: str,
    environment: Dict[str, str],
    description: str,
    code_bytes: bytes,
    tags: dict,
) -> str:
    """
    Create or update Lambda function.

    Args:
        lambda_client: Boto3 Lambda client
        function_name: Lambda function name
        role_arn: Execution role ARN
        handler: Handler function (e.g., 'main.handler')
        runtime: Python runtime version
        memory: Memory in MB
        timeout: Timeout in seconds
        architecture: CPU architecture (x86_64 or arm64)
        environment: Environment variables dict
        description: Function description
        code_bytes: ZIP file bytes
        tags: Resource tags dict

    Returns:
        Function ARN
    """
    # Create or update function
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role_arn,
            Handler=handler,
            Code={"ZipFile": code_bytes},
            Description=description,
            Timeout=timeout,
            MemorySize=memory,
            Architectures=[architecture],
            Environment={"Variables": environment},
            Tags=tags,
            Publish=True,  # Publish version
        )
        function_arn = response["FunctionArn"]
        logger.info(f"✓ Created Lambda function: {function_arn}")

    except lambda_client.exceptions.ResourceConflictException:
        # Function exists - update code and configuration
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response["Configuration"]["FunctionArn"]
        state = response["Configuration"]["State"]
        last_update = response["Configuration"]["LastUpdateStatus"]

        logger.info(f"✓ Lambda function already exists: {function_arn}")
        logger.info(f"  State: {state}, Last Update: {last_update}")

        # Wait for function to be ready for updates
        if state != "Active" or last_update == "InProgress":
            logger.info("  Waiting for function to be ready for updates...")
            waiter = lambda_client.get_waiter("function_active_v2")
            waiter.wait(FunctionName=function_name)
            logger.info("  Function is ready")

        # Update function code
        logger.info("  Updating function code...")
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=code_bytes,
            Publish=True,  # Publish new version
        )

        # Wait for code update to complete
        waiter = lambda_client.get_waiter("function_updated_v2")
        waiter.wait(FunctionName=function_name)
        logger.info("  ✓ Code updated successfully")

        # Update function configuration
        logger.info("  Updating function configuration...")
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role_arn,
            Handler=handler,
            Description=description,
            Timeout=timeout,
            MemorySize=memory,
            Environment={"Variables": environment},
        )

        # Wait for configuration update to complete
        waiter = lambda_client.get_waiter("function_updated_v2")
        waiter.wait(FunctionName=function_name)
        logger.info("  ✓ Configuration updated successfully")

    return function_arn


def delete_lambda_function(lambda_client, function_name: str):
    """
    Delete Lambda function.

    Args:
        lambda_client: Boto3 Lambda client
        function_name: Lambda function name
    """
    try:
        lambda_client.delete_function(FunctionName=function_name)
        logger.info(f"✓ Deleted Lambda function: {function_name}")
    except lambda_client.exceptions.ResourceNotFoundException:
        logger.info(f"  Lambda function does not exist: {function_name}")
    except Exception as e:
        logger.error(f"Failed to delete Lambda function {function_name}: {e}")


def test_lambda_function(lambda_client, function_name: str, test_event: dict) -> dict:
    """
    Test invoke Lambda function.

    Args:
        lambda_client: Boto3 Lambda client
        function_name: Lambda function name
        test_event: Test event payload

    Returns:
        Invocation response
    """
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(test_event),
    )

    payload = json.loads(response["Payload"].read())
    logger.info(f"Lambda test invocation: StatusCode={response['StatusCode']}")

    return payload
