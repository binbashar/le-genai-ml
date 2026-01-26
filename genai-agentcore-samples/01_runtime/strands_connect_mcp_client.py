from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient

mcp_client = MCPClient(lambda: aws_iam_streamablehttp_client(
    endpoint="https://translator-agent-gateway-mt0lrnrwuh.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
    aws_region="us-west-2",
    aws_profile="DataScientist-905418344519",
    aws_service="bedrock-agentcore"
))

with mcp_client:
    tools = mcp_client.list_tools_sync()
    print(f"Tools disponibles: {[t.tool_name for t in tools]}")
    
    agent = Agent(tools=tools)
    response = agent("What is the weather in Montevideo?")