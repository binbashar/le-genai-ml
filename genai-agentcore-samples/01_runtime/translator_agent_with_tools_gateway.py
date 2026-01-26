from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from typing import Literal, Dict, Any
from gateway_tool_wrapper import create_gateway_tools, load_gateway_arn_from_config

import yaml
import os

app = BedrockAgentCoreApp()

# Define the state for the graph
class AgentState(MessagesState):
    """State for the translator agent with tools"""
    # Add any additional state fields if needed

# Define the agent using LangGraph
def create_agent(config_file):
    # Read the config file yaml
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    """Create and configure the LangGraph agent with Gateway tools"""
    # Initialize Bedrock Claude model with tool binding
    llm = ChatBedrock(
        model_id=config["model_id"],
        model_kwargs={"temperature": config["temperature"]},
    )

    # Load Gateway ARN from config or environment
    gateway_arn = (
        config.get("gateway_arn") or
        os.getenv("AGENTCORE_GATEWAY_ARN") or
        load_gateway_arn_from_config()
    )
    
    if not gateway_arn:
        raise ValueError(
            "Gateway ARN not found. Please set it in config.yaml as 'gateway_arn' "
            "or set AGENTCORE_GATEWAY_ARN environment variable."
        )
    
    # Get region from config or environment
    region = config.get("region") or os.getenv("AWS_REGION", "us-west-2")
    
    # Create Gateway tools
    gateway_tools = create_gateway_tools(gateway_arn, region)
    
    # Create a mapping of tool names to Gateway tool instances for execution
    tool_map: Dict[str, Any] = {tool.name: tool for tool in gateway_tools}
    
    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(gateway_tools)

    # System message for translation with tool usage
    system_message = """You are a helpful translator with access to tools via AgentCore Gateway. You are able to answer three types of queries: 
    1. and 2. If the user asks about weather or wants to calculate text length, use the appropriate tools. 
    3. In any other case, asume the request is to translate the text to English, so just translate the text to English and return the translation and nothing else."""

    # Define the translator node
    def translator(state: AgentState):
        # Add system message if not already present
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages

        # Invoke LLM with tool binding
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Define tool execution node
    def tool_executor(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        tool_calls = []
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            tool_calls = last_message.tool_calls

        # Execute Gateway tools and create tool messages
        tool_messages = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Get Gateway tool from map
            gateway_tool = tool_map.get(tool_name)
            
            if gateway_tool:
                # Invoke Gateway tool via wrapper
                result = gateway_tool._run(**tool_args)
            else:
                result = f"Unknown tool: {tool_name}. Available tools: {list(tool_map.keys())}"

            tool_messages.append(ToolMessage(
                content=result,
                tool_call_id=tool_call["id"]
            ))

        return {"messages": tool_messages}

    # Define conditional routing
    def should_continue(state: AgentState) -> Literal["tools", END]:
        messages = state["messages"]
        last_message = messages[-1]

        # Check if the last message has tool calls
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return END

    # Create the graph
    graph_builder = StateGraph(AgentState)

    # Add nodes
    graph_builder.add_node("translator", translator)
    graph_builder.add_node("tools", tool_executor)

    # Add edges
    graph_builder.add_edge(START, "translator")
    graph_builder.add_conditional_edges("translator", should_continue)
    graph_builder.add_edge("tools", "translator")

    # Compile the graph
    return graph_builder.compile()


# Initialize the agent
agent = create_agent("config.yaml")


@app.entrypoint
def translate(payload, context):
    """
    Invoke the translator agent with tools
    """
    user_input = payload.get("prompt", "Hello")

    # Create the input in the format expected by LangGraph
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    # Extract the final message content
    return {"result": response["messages"][-1].content}


if __name__ == "__main__":
    app.run()
