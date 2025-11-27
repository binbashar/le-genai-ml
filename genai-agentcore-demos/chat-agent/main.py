"""
Chat Agent - Basic LangGraph agent with streaming and AgentCore Memory.

Demonstrates:
- LangGraph StateGraph with MessagesState
- AgentCoreMemorySaver for STM checkpointing
- Async streaming with proper checkpoint persistence
- Amazon Nova Lite model

This agent uses graph.ainvoke() to ensure proper checkpoint saving, then
streams the response tokens to the client. This guarantees conversation
history is persisted to AgentCore Memory.

Key Configuration:
- Environment variable BEDROCK_AGENTCORE_MEMORY_ID is set by AgentCore Runtime
- Uses langgraph-checkpoint-aws package for AgentCoreMemorySaver
- Requires thread_id and actor_id in config for proper checkpoint scoping
"""

import os
import uuid

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """You are a helpful AI assistant. Provide clear, concise responses.
You remember previous messages in our conversation and can reference them when relevant."""


def get_region() -> str:
    """Get AWS region with fallback chain."""
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-west-2"
    )


def create_chat_graph(checkpointer=None):
    """
    Create LangGraph with optional checkpointer for memory.

    The checkpointer automatically persists state after graph.invoke() or
    graph.ainvoke() completes. This is the key to proper memory persistence.

    Args:
        checkpointer: Optional AgentCoreMemorySaver for state persistence

    Returns:
        Compiled StateGraph
    """
    llm = ChatBedrock(
        model_id="us.amazon.nova-lite-v1:0",
        model_kwargs={"temperature": 0.7},
    )

    def chat_node(state: MessagesState):
        """Process messages and generate response."""
        messages = state["messages"]
        # Add system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("chat", chat_node)
    graph_builder.add_edge(START, "chat")
    graph_builder.add_edge("chat", END)

    return graph_builder.compile(checkpointer=checkpointer)


def _get_checkpointer(region: str):
    """
    Get AgentCoreMemorySaver if memory is configured.

    The BEDROCK_AGENTCORE_MEMORY_ID environment variable is automatically set
    by the AgentCore Runtime when memory is configured in .bedrock_agentcore.yaml.

    Returns:
        AgentCoreMemorySaver instance or None
    """
    # AgentCore Runtime sets BEDROCK_AGENTCORE_MEMORY_ID (not AGENTCORE_MEMORY_ID)
    memory_id = os.environ.get("BEDROCK_AGENTCORE_MEMORY_ID")

    if not memory_id:
        return None

    try:
        from langgraph_checkpoint_aws import AgentCoreMemorySaver

        return AgentCoreMemorySaver(memory_id, region_name=region)
    except ImportError:
        # langgraph-checkpoint-aws not installed
        return None
    except Exception:
        # Memory service unavailable
        return None


@app.entrypoint
async def chat(payload, context):
    """
    Main entrypoint with streaming response.

    Uses graph.ainvoke() to ensure proper checkpoint persistence, then
    streams the response content to the client. This pattern guarantees
    that conversation history is saved to AgentCore Memory.

    Payload format:
        {
            "prompt": "User message",
            "session_id": "optional-session-id",
            "actor_id": "optional-actor-id"
        }

    Yields:
        {"type": "thinking", "message": "..."}  - Progress updates
        {"type": "stream_token", "token": "...", "accumulated": "..."}  - Token stream
        {"type": "final", "result": "..."}  - Final response
        {"type": "error", "message": "..."}  - Errors
    """
    # Extract parameters
    user_message = payload.get("prompt") or payload.get("query", "")
    session_id = payload.get("session_id") or str(uuid.uuid4())
    actor_id = payload.get("actor_id", "user")

    # Validate input
    if not user_message:
        yield {"type": "error", "message": "No prompt provided."}
        return

    region = get_region()

    # Initialize checkpointer
    yield {"type": "thinking", "message": "Initializing memory..."}
    checkpointer = _get_checkpointer(region)

    memory_id = os.environ.get("BEDROCK_AGENTCORE_MEMORY_ID", "")
    if checkpointer:
        yield {"type": "thinking", "message": f"Memory enabled: {memory_id}"}
    else:
        yield {"type": "thinking", "message": "Memory not configured"}

    # Create graph with checkpointer
    graph = create_chat_graph(checkpointer)

    # Config maps to AgentCore Memory identifiers:
    # - thread_id -> session_id (conversation thread)
    # - actor_id -> actor_id (user identifier)
    # Both are REQUIRED for AgentCoreMemorySaver to work properly
    config = {"configurable": {"thread_id": session_id, "actor_id": actor_id}}

    yield {"type": "thinking", "message": "Loading conversation history..."}

    # Log memory status for debugging
    if checkpointer:
        try:
            state = graph.get_state(config)
            if state.values:
                msg_count = len(state.values.get("messages", []))
                yield {
                    "type": "thinking",
                    "message": f"Found {msg_count} messages in history",
                }
            else:
                yield {"type": "thinking", "message": "Starting fresh conversation"}
        except Exception:
            yield {"type": "thinking", "message": "Starting fresh conversation"}

    yield {"type": "thinking", "message": "Generating response..."}

    # Use ainvoke() to ensure proper checkpoint persistence
    # This is crucial - graph.ainvoke() triggers the checkpointer.put() method
    # after the graph execution completes, saving the full conversation state
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=user_message)]},
            config,
        )
    except Exception as e:
        yield {"type": "error", "message": f"Generation error: {str(e)[:200]}"}
        return

    # Extract the response from the graph result
    messages = result.get("messages", [])
    if not messages:
        yield {"type": "error", "message": "No response generated"}
        return

    # Get the last AI message (the response)
    ai_response = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            ai_response = msg
            break

    if not ai_response:
        yield {"type": "error", "message": "No AI response in result"}
        return

    # Extract content from the response
    full_response = ""
    if isinstance(ai_response.content, str):
        full_response = ai_response.content
    elif isinstance(ai_response.content, list):
        # Handle Nova's list-based content blocks
        for block in ai_response.content:
            if isinstance(block, dict) and "text" in block:
                full_response += block["text"]
            elif isinstance(block, str):
                full_response += block

    # Stream the response to the client (simulated streaming of complete response)
    # This provides a consistent streaming interface even though we got the full response
    chunk_size = 20  # Characters per chunk for smoother streaming effect
    accumulated = ""
    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i : i + chunk_size]
        accumulated += chunk
        yield {
            "type": "stream_token",
            "token": chunk,
            "accumulated": accumulated,
        }

    # The checkpoint was automatically saved by graph.ainvoke()
    # No manual save needed - this is the key benefit of using invoke()

    yield {
        "type": "final",
        "result": full_response,
        "metadata": {
            "session_id": session_id,
            "actor_id": actor_id,
            "memory_enabled": checkpointer is not None,
            "history_count": len(messages),
        },
    }


if __name__ == "__main__":
    app.run()
