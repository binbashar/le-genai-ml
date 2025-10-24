import json
import logging
from datetime import datetime

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from tools import (
    collect_broker_preferences_interactively,
    compose_context,
    create_memory,
    create_memory_tools,
    generate_market_summary_for_broker,
    get_broker_card_template,
    get_stock_data,
    parse_broker_profile_from_message,
    retrieve_context_parallel,
    search_news,
)

app = BedrockAgentCoreApp()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Patch OpenTelemetry bug: _decode_tool_use tries to json.loads() already-parsed dicts
# This happens when Claude returns tool_use blocks with dict inputs
try:
    from opentelemetry.instrumentation.botocore.extensions import bedrock_utils # type: ignore

    original_decode_tool_use = bedrock_utils._decode_tool_use

    def patched_decode_tool_use(tool_use):
        """Patched version that checks if input is already a dict before parsing"""
        if "input" in tool_use:
            # Only parse if it's a string, skip if already a dict
            if isinstance(tool_use["input"], str):
                tool_use["input"] = json.loads(tool_use["input"])
            # If it's already a dict, leave it as-is
        return tool_use

    bedrock_utils._decode_tool_use = patched_decode_tool_use
    logger.info("✅ Applied OpenTelemetry bedrock_utils patch for tool_use handling")
except Exception as e:
    logger.warning(f"Could not apply OpenTelemetry patch: {e}")

def create_market_trends_agent(session_id: str, actor_id: str):
    """Create and configure the LangGraph market trends agent with memory

    Args:
        session_id: Session ID for this conversation
        actor_id: Authenticated actor ID for memory operations
    """
    from config import BedrockModelCatalog, get_bedrock_model

    memory_client, memory_id = create_memory()

    model = get_bedrock_model(
        model=BedrockModelCatalog.NOVA_LITE,
        framework="langchain",
    )

    memory_tools = create_memory_tools(memory_client, memory_id, session_id, actor_id)

    tools = [
        get_stock_data,
        search_news,
        parse_broker_profile_from_message,
        generate_market_summary_for_broker,
        get_broker_card_template,
        collect_broker_preferences_interactively,
    ] + memory_tools
    llm_with_tools = model.bind_tools(tools)

    system_message = """You are an expert market intelligence analyst providing real-time market data and personalized investment insights.

<memory_behavior>
Both conversation history and broker profile are automatically injected in <context> tags.
Context contains <conversation_history> (recent exchanges) and <broker_profile> (preferences, risk tolerance).
When users share new preferences, use update_broker_financial_interests() to store them.
</memory_behavior>

<tool_usage>
Market Data: get_stock_data(symbol), search_news(query, news_source)
Memory: update_broker_financial_interests(info)
Broker Tools: parse_broker_profile_from_message(), generate_market_summary_for_broker(), get_broker_card_template(), collect_broker_preferences_interactively()
</tool_usage>

<response_style>
Deliver professional, data-driven analysis tailored to user preferences when available.
</response_style>"""

    # Define the chatbot node with automatic conversation saving and context injection
    async def chatbot(state: MessagesState):
        raw_messages = state["messages"]

        # print everything in state, to debug if we are saving tool calls in addition to the conversation
        logger.debug(f"State: {state}")

        # Remove any existing system messages to avoid duplicates
        filtered_messages = [
            msg for msg in raw_messages if not isinstance(msg, SystemMessage)
        ]

        # AUTOMATIC CONTEXT INJECTION: Retrieve all context (STM + LTM) in parallel
        # This happens BEFORE the LLM sees the message, ensuring context is always available
        if filtered_messages and isinstance(filtered_messages[-1], HumanMessage):
            latest_user_message = filtered_messages[-1]
            user_query = (
                latest_user_message.content
                if isinstance(latest_user_message.content, str)
                else ""
            )

            if user_query:
                # Retrieve all context in parallel from AgentCore Memory
                context_dict = await retrieve_context_parallel(
                    memory_client=memory_client,
                    memory_id=memory_id,
                    session_id=session_id,
                    actor_id=actor_id,
                )

                context_str = compose_context(context_dict)

                if context_str:
                    logger.info(
                        f"Injecting {len(context_str)} characters of context from memory"
                    )
                    latest_user_message.content = context_str + user_query

        messages_to_filter = filtered_messages
        filtered_messages = []
        i = 0
        while i < len(messages_to_filter):
            msg = messages_to_filter[i]

            # Check if message has content (for regular messages)
            if (
                hasattr(msg, "content")
                and isinstance(msg.content, str)
                and msg.content.strip()
            ):
                filtered_messages.append(msg)
            # Check if message has tool_calls (for tool_use messages)
            elif hasattr(msg, "tool_calls") and msg.tool_calls:
                filtered_messages.append(msg)
            # Check if message has tool_call_id (for tool_result messages)
            elif hasattr(msg, "tool_call_id") and msg.tool_call_id:
                filtered_messages.append(msg)
            # Check for content list with tool blocks
            elif hasattr(msg, "content") and isinstance(msg.content, list):
                # Keep messages with tool content blocks
                has_tool_content = any(
                    isinstance(block, dict)
                    and block.get("type") in ["tool_use", "tool_result"]
                    for block in msg.content
                )
                if has_tool_content:
                    filtered_messages.append(msg)
                else:
                    # Check if any text blocks have content
                    has_text_content = any(
                        isinstance(block, dict)
                        and block.get("type") == "text"
                        and block.get("text", "").strip()
                        for block in msg.content
                    )
                    if has_text_content:
                        filtered_messages.append(msg)
                    else:
                        logger.warning(
                            f"Filtered out empty message: {type(msg).__name__}"
                        )
            else:
                logger.warning(f"Filtered out empty message: {type(msg).__name__}")

            i += 1

        # Always ensure SystemMessage is first
        messages = [SystemMessage(content=system_message)] + filtered_messages

        # Get response from model with tools bound
        logger.info("🤖 Invoking LLM with tools...")
        response = llm_with_tools.invoke(messages)

        # Log tool usage for debugging
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "unknown")
                tool_args = tool_call.get("args", {})
                logger.info(
                    f"🔧 LLM requested tool: {tool_name} with args: {tool_args}"
                )
        else:
            logger.info("💬 LLM returned text response (no tools)")

        # Save conversation to AgentCore Memory
        latest_user_message = next(
            (
                msg.content
                for msg in reversed(messages)
                if isinstance(msg, HumanMessage)
            ),
            None,
        )

        # Convert to strings, skip if empty
        user_message_text = str(latest_user_message) if latest_user_message else ""
        response_content = str(response.content) if response.content else ""

        logger.info(
            f"💾 STM DEBUG: Preparing to save conversation - user_msg_length={len(user_message_text)}, response_length={len(response_content)}"
        )

        if user_message_text.strip() and response_content.strip():
            conversation = [
                (user_message_text, "USER"),
                (response_content, "ASSISTANT"),
            ]

            logger.info(
                f"💾 STM DEBUG: Calling create_event for session={session_id}, actor={actor_id}"
            )
            try:
                result = memory_client.create_event(
                    memory_id=memory_id,
                    actor_id=actor_id,
                    session_id=session_id,
                    messages=conversation,
                )
                logger.info(
                    f"✅ STM DEBUG: Conversation saved successfully - event_id={result.get('eventId', 'unknown')}"
                )
            except Exception as e:
                logger.error(
                    f"❌ STM DEBUG: Error saving conversation to memory: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"⚠️ STM DEBUG: Skipping save - empty messages (user: {len(user_message_text)}, response: {len(response_content)})"
            )

        # Return updated messages
        return {"messages": raw_messages + [response]}

    # Create the graph
    graph_builder = StateGraph(MessagesState)

    # Add nodes
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))

    # Add edges
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")

    # Set entry point
    graph_builder.set_entry_point("chatbot")

    # Compile the graph
    return graph_builder.compile()


def extract_actor_id(context) -> str:  # noqa: ARG001
    """
    Extract actor ID from request context.

    For demo purposes, returns hardcoded 'demo-user'.
    In production, extract from authenticated request headers:

    Example production implementation:
        headers = context.request_headers or {}
        return headers.get('X-Amzn-Bedrock-AgentCore-Runtime-User-Id', 'demo-user')

    Args:
        context: AgentCore Runtime context object (unused in demo mode)

    Returns:
        str: Actor ID for memory operations
    """
    # Demo mode: hardcoded actor for simplicity
    return "demo-user"


@app.entrypoint
async def market_trends_agent_runtime(payload, context):
    """
    Invoke the market trends agent with streaming for AgentCore Runtime

    Expects payload with:
        - prompt: User input message
        - session_id: Session identifier (optional, will generate if not provided)

    Yields streaming events:
        - thinking: Tool execution progress
        - stream_token: Individual LLM tokens
        - final: Complete response with metadata
        - error: Any exceptions
    """
    user_input = payload.get("prompt")
    session_id = payload.get("session_id")

    if not session_id:
        session_id = f"default-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.warning(f"No session_id provided, using generated: {session_id}")

    # Extract actor ID from context (demo: always "demo-user")
    actor_id = extract_actor_id(context)

    try:
        agent = create_market_trends_agent(session_id, actor_id)

        # Track tool executions and accumulated response
        current_tool = None
        accumulated_response = ""
        final_response = None
        pending_tool_calls = []  # Track tools that will be executed

        # Stream events from LangGraph
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=user_input)]}, version="v2"
        ):
            event_type = event.get("event")

            # Detect tool calls early - when LLM response includes tool_calls
            # This fires BEFORE on_tool_start, ensuring the message appears before execution
            if event_type == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                if output and hasattr(output, "tool_calls") and output.tool_calls:
                    # LLM wants to use tools - emit thinking messages immediately
                    for tool_call in output.tool_calls:
                        tool_name = tool_call.get("name", "")
                        if tool_name and tool_name not in pending_tool_calls:
                            pending_tool_calls.append(tool_name)
                            logger.info(f"🔧 LLM requesting tool: {tool_name}")

                            # Map tool names to friendly messages
                            tool_messages = {
                                "get_stock_data": "📊 Getting stock data...",
                                "search_news": "📰 Searching news sources...",
                                "update_broker_financial_interests": "💾 Updating broker preferences...",
                                "parse_broker_profile_from_message": "📋 Parsing broker card...",
                            }
                            message = tool_messages.get(
                                tool_name, f"⚙️ Using {tool_name}..."
                            )
                            yield {"type": "thinking", "message": message}

            # Tool execution started (keep for tracking current_tool)
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "")
                if tool_name:
                    current_tool = tool_name
                    logger.info(f"🔧 Tool execution starting: {tool_name}")

            # Tool execution completed
            elif event_type == "on_tool_end":
                if current_tool:
                    logger.info(f"✅ Tool execution completed: {current_tool}")
                    yield {"type": "thinking", "message": "✓ Completed"}
                    # Remove completed tool from pending list
                    if current_tool in pending_tool_calls:
                        pending_tool_calls.remove(current_tool)
                    current_tool = None

            # LLM streaming tokens
            elif event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # Check if this chunk contains tool_calls (early detection)
                    has_tool_calls = False
                    if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                        has_tool_calls = True
                        # Tool calls detected during streaming - emit thinking messages immediately
                        for tool_call in chunk.tool_calls:
                            tool_name = tool_call.get("name", "")
                            if tool_name and tool_name not in pending_tool_calls:
                                pending_tool_calls.append(tool_name)
                                logger.info(
                                    f"🔧 Tool detected during streaming: {tool_name}"
                                )

                                # Map tool names to friendly messages
                                tool_messages = {
                                    "get_stock_data": "📊 Getting stock data...",
                                    "search_news": "📰 Searching news sources...",
                                    "update_broker_financial_interests": "💾 Updating broker preferences...",
                                    "parse_broker_profile_from_message": "📋 Parsing broker card...",
                                }
                                message = tool_messages.get(
                                    tool_name, f"⚙️ Using {tool_name}..."
                                )
                                yield {"type": "thinking", "message": message}

                    # Only skip tokens that actually contain tool_calls
                    # Don't skip tokens just because a tool is executing - those are from the second LLM call
                    # analyzing the tool results and should stream normally
                    if not has_tool_calls:
                        # Handle different content formats (Claude returns string)
                        token_text = ""
                        if isinstance(chunk.content, str):
                            token_text = chunk.content
                        elif isinstance(chunk.content, list):
                            # Handle list-based content
                            for block in chunk.content:
                                if isinstance(block, dict) and "text" in block:
                                    token_text += block["text"]
                                elif isinstance(block, str):
                                    token_text += block

                        if token_text:
                            accumulated_response += token_text
                            yield {
                                "type": "stream_token",
                                "token": token_text,
                                "accumulated": accumulated_response,
                            }

            # Chain completed
            elif event_type == "on_chain_end":
                # Check if this is the final output
                output = event.get("data", {}).get("output")
                if output and isinstance(output, dict) and "messages" in output:
                    messages = output["messages"]
                    if messages:
                        content = messages[-1].content

                        # Handle both string and list content formats
                        if isinstance(content, list):
                            # Extract text from content blocks
                            response_text = ""
                            for block in content:
                                if isinstance(block, dict) and "text" in block:
                                    response_text += block["text"]
                                elif isinstance(block, str):
                                    response_text += block
                            final_response = response_text
                        else:
                            final_response = content

        # Send final response
        if final_response or accumulated_response:
            yield {
                "type": "final",
                "result": final_response or accumulated_response,
                "metadata": {"session_id": session_id},
            }

    except Exception as e:
        logger.error(f"Error in streaming agent: {e}", exc_info=True)
        yield {"type": "error", "message": f"Agent error: {str(e)}"}