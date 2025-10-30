"""
AgentCore Gateway creation and configuration module.

Handles:
- Gateway creation with OAuth/IAM authentication
- Gateway target creation for Lambda tools
- Tool schema registration
"""

import logging
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


def create_gateway(
    agentcore_client,
    name: str,
    description: str,
    role_arn: str,
    debug_mode: bool,
    tags: dict,
    cognito_config: Optional[dict] = None,
) -> Tuple[str, str]:
    """
    Create AgentCore Gateway with authentication.

    Args:
        agentcore_client: Boto3 bedrock-agentcore-control client
        name: Gateway name
        description: Gateway description
        role_arn: Gateway service role ARN
        debug_mode: Enable debug logging
        tags: Resource tags dict
        cognito_config: Optional Cognito OAuth configuration
                       Format: {'discoveryUrl': '...', 'clientId': '...'}

    Returns:
        Tuple of (gateway_id, gateway_endpoint)
    """
    gateway_config = {
        "name": name,
        "description": description,
        "roleArn": role_arn,
        "protocolType": "MCP",
        "tags": tags,
    }

    if debug_mode:
        gateway_config["exceptionLevel"] = "DEBUG"

    # Add authentication configuration
    if cognito_config:
        gateway_config["authorizerType"] = "CUSTOM_JWT"

        # Support both old format (single clientId) and new format (allowedClients list)
        allowed_clients = cognito_config.get('allowedClients') or [cognito_config.get('clientId')]

        gateway_config["authorizerConfiguration"] = {
            "customJWTAuthorizer": {
                "discoveryUrl": cognito_config["discoveryUrl"],
                "allowedClients": allowed_clients,
            }
        }
        logger.info(
            f"  Using Cognito OAuth (User Pool: {cognito_config.get('userPoolId', 'N/A')})"
        )
        logger.info(f"  Allowed clients: {len(allowed_clients)} client(s)")
        if cognito_config.get('m2m_client_id'):
            logger.info("  M2M authentication: Enabled")
    else:
        gateway_config["authorizerType"] = "AWS_IAM"
        logger.info("  Using IAM authentication (no OAuth)")

    try:
        response = agentcore_client.create_gateway(**gateway_config)
        gateway_id = response["gatewayId"]
        gateway_endpoint = response["gatewayUrl"]
        logger.info(f"✓ Created Gateway: {gateway_id}")
        logger.info(f"  Endpoint: {gateway_endpoint}")

    except Exception as e:
        if "AlreadyExists" in str(e) or "ConflictException" in str(e):
            # Get existing gateway
            try:
                list_response = agentcore_client.list_gateways()
                gateways = list_response.get(
                    "gateways", list_response.get("gatewayList", [])
                )
                gateway = next((g for g in gateways if g.get("name") == name), None)

                if gateway:
                    gateway_id = gateway["gatewayId"]
                    gateway_endpoint = gateway.get(
                        "gatewayUrl", gateway.get("gatewayEndpoint", "")
                    )
                    logger.info(f"✓ Gateway already exists: {gateway_id}")
                    logger.info(f"  Endpoint: {gateway_endpoint}")
                else:
                    raise ValueError(
                        f"Gateway '{name}' exists but could not be retrieved"
                    )
            except Exception as list_error:
                logger.error(f"  Failed to list gateways: {list_error}")
                logger.info(f"  Gateway '{name}' likely exists but cannot be retrieved")
                raise ValueError(
                    "Gateway exists but cannot be retrieved. Please check AWS console."
                )
        else:
            raise

    return gateway_id, gateway_endpoint


def create_gateway_target(
    agentcore_client,
    gateway_id: str,
    target_name: str,
    target_description: str,
    lambda_arn: str,
    tool_schema: dict,
) -> str:
    """
    Add Lambda target to Gateway.

    Args:
        agentcore_client: Boto3 bedrock-agentcore-control client
        gateway_id: Gateway identifier
        target_name: Target name (prefix for tool names)
        target_description: Target description
        lambda_arn: Lambda function ARN
        tool_schema: Tool schema (JSON Schema format)

    Returns:
        Target ID
    """
    try:
        response = agentcore_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target_name,
            description=target_description,
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {"inlinePayload": [tool_schema]},
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )
        target_id = response.get("targetId") or response.get("target", {}).get(
            "targetId"
        )
        tool_name = tool_schema["name"]
        logger.info(f"✓ Created Gateway target: {target_id}")
        logger.info(f"  Tool exposed as: {target_name}___{tool_name}")

    except Exception as e:
        if "AlreadyExists" in str(e) or "ConflictException" in str(e):
            try:
                list_response = agentcore_client.list_gateway_targets(
                    gatewayIdentifier=gateway_id
                )
                targets_list = list_response.get(
                    "targets", list_response.get("targetList", [])
                )
                target = next(
                    (t for t in targets_list if t.get("name") == target_name), None
                )

                if target:
                    target_id = target.get("targetId")
                    tool_name = tool_schema["name"]
                    logger.info(f"✓ Gateway target already exists: {target_id}")
                    logger.info(f"  Tool exposed as: {target_name}___{tool_name}")
                else:
                    target_id = f"existing-{target_name}"
                    logger.warning("  Target exists but could not retrieve ID")
            except Exception:
                tool_name = tool_schema["name"]
                target_id = f"existing-{target_name}"
                logger.info(f"✓ Gateway target '{target_name}' already exists")
                logger.info(f"  Tool exposed as: {target_name}___{tool_name}")
        else:
            raise

    return target_id


def delete_gateway(agentcore_client, gateway_id: str):
    """
    Delete AgentCore Gateway and all targets.

    Args:
        agentcore_client: Boto3 bedrock-agentcore-control client
        gateway_id: Gateway identifier
    """
    try:
        targets = agentcore_client.list_gateway_targets(gatewayIdentifier=gateway_id)
        for target in targets.get("targets", []):
            try:
                agentcore_client.delete_gateway_target(
                    gatewayIdentifier=gateway_id, targetIdentifier=target["targetId"]
                )
                logger.info(f"  Deleted target: {target['name']}")
            except Exception as e:
                logger.error(f"  Failed to delete target {target['name']}: {e}")

        agentcore_client.delete_gateway(gatewayIdentifier=gateway_id)
        logger.info(f"✓ Deleted Gateway: {gateway_id}")

    except agentcore_client.exceptions.ResourceNotFoundException:
        logger.info(f"  Gateway does not exist: {gateway_id}")
    except Exception as e:
        logger.error(f"Failed to delete Gateway {gateway_id}: {e}")
