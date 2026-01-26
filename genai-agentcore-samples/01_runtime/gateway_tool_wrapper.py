"""
Custom LangChain tool wrapper for AgentCore Gateway tools.
This module provides a BaseTool implementation that invokes Gateway tools via AWS SDK.
"""
import json
import logging
import os
from typing import Any, Dict, Optional, Type

import boto3
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GatewayToolInput(BaseModel):
    """Input schema for Gateway tool invocation."""
    arguments: Dict[str, Any] = Field(description="Tool arguments")


class GatewayTool(BaseTool):
    """
    LangChain tool wrapper for AgentCore Gateway tools.
    
    This tool invokes Gateway tools via the AWS Bedrock AgentCore SDK
    instead of calling local functions directly.
    """
    
    gateway_arn: str = Field(description="ARN of the AgentCore Gateway")
    tool_name: str = Field(description="Name of the tool in Gateway")
    region: str = Field(default="us-west-2", description="AWS region")
    client: Optional[Any] = Field(default=None, description="Boto3 bedrock-agentcore client")
    
    def __init__(self, gateway_arn: str, tool_name: str, description: str, 
                 region: str = "us-west-2", **kwargs):
        """
        Initialize Gateway tool wrapper.
        
        Args:
            gateway_arn: ARN of the AgentCore Gateway
            tool_name: Name of the tool as registered in Gateway
            description: Tool description
            region: AWS region
        """
        # Initialize boto3 client for Gateway invocations (data plane)
        # Note: Control operations use "bedrock-agentcore-control", 
        # but tool invocations use "bedrock-agentcore"
        client = boto3.client("bedrock-agentcore", region_name=region)
        
        # Determine input schema from tool name
        input_schema = self._get_input_schema(tool_name)
        
        super().__init__(
            name=tool_name,
            description=description,
            args_schema=input_schema,
            gateway_arn=gateway_arn,
            tool_name=tool_name,
            region=region,
            client=client,
            **kwargs
        )
    
    def _get_input_schema(self, tool_name: str) -> Type[BaseModel]:
        """Get input schema class based on tool name."""
        if tool_name == "get_current_weather":
            class WeatherInput(BaseModel):
                location: str = Field(description="The location to get weather for")
            return WeatherInput
        elif tool_name == "calculate_length":
            class LengthInput(BaseModel):
                text: str = Field(description="The text string to calculate length for")
            return LengthInput
        else:
            # Generic schema for unknown tools
            class GenericInput(BaseModel):
                arguments: Dict[str, Any] = Field(description="Tool arguments")
            return GenericInput
    
    def _invoke_gateway_tool(self, arguments: Dict[str, Any]) -> str:
        """
        Invoke Gateway tool via AWS SDK.
        
        Args:
            arguments: Tool arguments dictionary
            
        Returns:
            Tool result as string
        """
        try:
            logger.info(f"Invoking Gateway tool '{self.tool_name}' with arguments: {arguments}")
            
            # Invoke Gateway using MCP protocol format
            # Note: The exact API method and parameter format may vary.
            # Check AWS Bedrock AgentCore API documentation for the correct format.
            try:
                response = self.client.invoke_gateway(
                    gatewayArn=self.gateway_arn,
                    toolCall={
                        "name": self.tool_name,
                        "arguments": json.dumps(arguments) if isinstance(arguments, dict) else arguments
                    }
                )
            except AttributeError:
                # Try alternative method name if invoke_gateway doesn't exist
                try:
                    response = self.client.invoke_tool(
                        gatewayArn=self.gateway_arn,
                        toolName=self.tool_name,
                        arguments=arguments
                    )
                except AttributeError:
                    raise AttributeError(
                        f"Could not find Gateway invocation method. "
                        f"Please check AWS Bedrock AgentCore API documentation. "
                        f"Tried: invoke_gateway, invoke_tool"
                    )
            
            # Parse response
            # Gateway returns response in MCP format
            result_body = response.get("result", {})
            
            # Handle different response formats
            if isinstance(result_body, str):
                try:
                    result_body = json.loads(result_body)
                except json.JSONDecodeError:
                    return result_body
            
            # Extract result from response
            if isinstance(result_body, dict):
                # Try common response formats
                result = (
                    result_body.get("result") or
                    result_body.get("body") or
                    result_body.get("response") or
                    json.dumps(result_body)
                )
            else:
                result = str(result_body)
            
            logger.info(f"Gateway tool '{self.tool_name}' returned: {result[:100]}...")
            return result
            
        except Exception as e:
            error_msg = f"Error invoking Gateway tool '{self.tool_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"
    
    def _run(self, **kwargs: Any) -> str:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool result as string
        """
        return self._invoke_gateway_tool(kwargs)
    
    async def _arun(self, **kwargs: Any) -> str:
        """
        Async execution of the tool.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool result as string
        """
        # For now, use sync implementation
        # In production, you might want to use aioboto3 for async AWS calls
        return self._run(**kwargs)


def create_gateway_tools(gateway_arn: str, region: str = "us-west-2") -> list[GatewayTool]:
    """
    Create Gateway tool wrappers for all registered tools.
    
    Args:
        gateway_arn: ARN of the AgentCore Gateway
        region: AWS region
        
    Returns:
        List of GatewayTool instances
    """
    tools = [
        GatewayTool(
            gateway_arn=gateway_arn,
            tool_name="get_current_weather",
            description="Get current weather for a location. This is a dummy tool for testing AgentCore Gateway deployment.",
            region=region
        ),
        GatewayTool(
            gateway_arn=gateway_arn,
            tool_name="calculate_length",
            description="Calculate the length of a text string. This is a dummy tool for testing AgentCore Gateway deployment.",
            region=region
        )
    ]
    
    return tools


def load_gateway_arn_from_config() -> Optional[str]:
    """
    Load Gateway ARN from configuration file.
    
    Returns:
        Gateway ARN if found, None otherwise
    """
    try:
        from pathlib import Path
        import yaml
        
        # Try loading from gateway_arn.json first
        gateway_file = Path(__file__).parent / "gateway_arn.json"
        if gateway_file.exists():
            with open(gateway_file) as f:
                data = json.load(f)
                return data.get("gatewayArn")
        
        # Try loading from config.yaml
        config_file = Path(__file__).parent / "config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                return config.get("gateway_arn")
        
        # Try environment variable
        return os.getenv("AGENTCORE_GATEWAY_ARN")
        
    except Exception as e:
        logger.warning(f"Could not load Gateway ARN from config: {e}")
        return None

