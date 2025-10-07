from langgraph.graph import StateGraph, MessagesState
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


# Define the agent using LangGraph
def create_agent():
    """Create and configure the LangGraph agent"""
    # Initialize Bedrock Claude model
    llm = ChatBedrock(
        model_id="us.amazon.nova-micro-v1:0",
        model_kwargs={"temperature": 0.1},
    )

    # System message for translation
    system_message = "You are a translator. Translate the user's message to English. Return ONLY the English translation, nothing else."

    # Define the translator node
    def translator(state: MessagesState):
        # Add system message if not already present
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages

        response = llm.invoke(messages)
        return {"messages": [response]}

    # Create the graph
    graph_builder = StateGraph(MessagesState)

    # Add node
    graph_builder.add_node("translator", translator)

    # Set entry point
    graph_builder.set_entry_point("translator")

    # Compile the graph
    return graph_builder.compile()


# Initialize the agent
agent = create_agent()


@app.entrypoint
def translate(payload, context):
    """
    Invoke the translator agent with a payload
    """
    user_input = payload.get("prompt", "Hello")

    # Create the input in the format expected by LangGraph
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    # Extract the final message content
    return {"result": response["messages"][-1].content}


if __name__ == "__main__":
    app.run()
