#!/usr/bin/env python3
"""
Local chat interface for Market Trends Agent
Interactive chat without AWS deployment - runs locally with your credentials
"""

import asyncio
import logging
from datetime import datetime

from langchain_core.messages import HumanMessage
from market_trends_agent import create_market_trends_agent
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

# Enable debug logging to see STM operations
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

console = Console()
logger = logging.getLogger(__name__)


class MarkdownStreamRenderer:
    """Handles incremental markdown rendering with Rich Live display"""

    def __init__(self):
        self.items = []  # List of (type, content) tuples to maintain chronological order
        self.current_response_buffer = ""  # Buffer for accumulating response tokens
        self.live = None

    def start(self):
        """Start the live display"""
        self.live = Live(console=console, auto_refresh=False)
        self.live.start()

    def stop(self):
        """Stop the live display"""
        if self.live:
            self.live.stop()
            self.live = None

    def add_thinking(self, message: str):
        """Add a thinking message inline to the conversation"""
        # Flush current response buffer before adding thinking message
        if self.current_response_buffer:
            self.items.append(("response", self.current_response_buffer))
            self.current_response_buffer = ""

        # Add thinking message to timeline
        self.items.append(("thinking", message))
        self._update_display()

    def add_token(self, token: str):
        """Add a token to the accumulated text"""
        self.current_response_buffer += token
        self._update_display()

    def _update_display(self):
        """Update the live display with current content"""
        if not self.live:
            return

        # Build composite view in chronological order
        renderables = []

        # Always add "Agent:" label at the beginning if we have content
        if self.items or self.current_response_buffer:
            renderables.append(Text("Agent:", style="bold magenta"))
            renderables.append(Text())  # Empty line after label

        prev_type = None

        for item_type, content in self.items:
            # Add spacing between thinking messages and response content
            if prev_type == "thinking" and item_type == "response":
                renderables.append(Text())  # Empty line for spacing

            if item_type == "thinking":
                # Render thinking message with dim style
                renderables.append(Text(content, style="dim white"))
            elif item_type == "response":
                # Render response content as markdown
                try:
                    renderables.append(Markdown(content))
                except Exception:
                    renderables.append(Text(content))

            prev_type = item_type

        # Add current response buffer (in progress)
        if self.current_response_buffer:
            # Add spacing if previous item was a thinking message
            if prev_type == "thinking":
                renderables.append(Text())  # Empty line for spacing

            try:
                renderables.append(Markdown(self.current_response_buffer))
            except Exception:
                renderables.append(Text(self.current_response_buffer))

        # Update live display with composite view
        if renderables:
            self.live.update(Group(*renderables), refresh=True)


class LocalStreamingHandler:
    """Handles streaming events from LangGraph's astream_events"""

    def __init__(self):
        self.renderer = MarkdownStreamRenderer()
        self.pending_tool_calls = []
        self.current_tool = None

    async def handle_stream(self, agent, user_query: str):
        """
        Process streaming events from LangGraph agent

        Args:
            agent: Compiled LangGraph agent
            user_query: User's input message

        Returns:
            str: Final response text
        """
        self.renderer.start()
        accumulated_response = ""
        final_response = None

        try:
            # Stream events from LangGraph
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=user_query)]}, version="v2"
            ):
                event_type = event.get("event")

                # Detect tool calls early - when LLM response includes tool_calls
                if event_type == "on_chat_model_end":
                    output = event.get("data", {}).get("output")
                    if output and hasattr(output, "tool_calls") and output.tool_calls:
                        # LLM wants to use tools - emit thinking messages immediately
                        for tool_call in output.tool_calls:
                            tool_name = tool_call.get("name", "")
                            if tool_name and tool_name not in self.pending_tool_calls:
                                self.pending_tool_calls.append(tool_name)
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
                                self.renderer.add_thinking(message)

                # Tool execution started
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name:
                        self.current_tool = tool_name
                        logger.info(f"🔧 Tool execution starting: {tool_name}")

                # Tool execution completed
                elif event_type == "on_tool_end":
                    if self.current_tool:
                        logger.info(f"✅ Tool execution completed: {self.current_tool}")
                        self.renderer.add_thinking("✓ Completed")
                        # Remove completed tool from pending list
                        if self.current_tool in self.pending_tool_calls:
                            self.pending_tool_calls.remove(self.current_tool)
                        self.current_tool = None

                # LLM streaming tokens
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Check if this chunk contains tool_calls
                        has_tool_calls = False
                        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                            has_tool_calls = True
                            # Tool calls detected during streaming
                            for tool_call in chunk.tool_calls:
                                tool_name = tool_call.get("name", "")
                                if (
                                    tool_name
                                    and tool_name not in self.pending_tool_calls
                                ):
                                    self.pending_tool_calls.append(tool_name)
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
                                    self.renderer.add_thinking(message)

                        # Only skip tokens that actually contain tool_calls
                        # (Don't skip tokens just because a tool is executing - those are from the second LLM call)
                        if not has_tool_calls:
                            # Handle different content formats
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
                                self.renderer.add_token(token_text)

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

        finally:
            self.renderer.stop()
            # Add spacing after response before next prompt
            print("\n")

        return final_response or accumulated_response


async def multi_turn_chat():
    """
    Multi-turn chat session with persistent session ID to test STM
    """
    # Create SAME session ID for entire conversation
    session_id = f"local-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    actor_id = "demo-user"

    print("\n" + "=" * 80)
    print("MARKET TRENDS AGENT - LOCAL MULTI-TURN CHAT (STM DEBUG MODE)")
    print("=" * 80)
    print(f"\nSession ID: {session_id}")
    print(f"Actor ID: {actor_id}")
    print("\nType 'quit' to exit, 'clear' to start new session")
    print("=" * 80 + "\n")

    # Create agent ONCE for entire session
    agent = create_market_trends_agent(session_id, actor_id)

    turn = 0
    while True:
        try:
            # Get user input with styled prompt
            console.print(Text("You:", style="bold magenta"), end=" ")
            user_query = input().strip()

            if not user_query:
                continue

            if user_query.lower() in ["quit", "exit"]:
                print("\nGoodbye!\n")
                break

            if user_query.lower() == "clear":
                print("\nStarting new session...\n")
                session_id = f"local-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                agent = create_market_trends_agent(session_id, actor_id)
                turn = 0
                print(f"New Session ID: {session_id}\n")
                continue

            turn += 1
            print(f"\n[Turn {turn}]\n")

            # Invoke agent with streaming
            handler = LocalStreamingHandler()
            await handler.handle_stream(agent, user_query)

        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!\n")
            break
        except Exception as e:
            print(f"\n[Error: {e}]\n")
            logging.exception("Error in chat loop")


async def test_streaming_local(user_query: str):
    """
    Test the agent with streaming output locally (single query)

    Args:
        user_query: The user's question/prompt
    """
    print("\n" + "=" * 60)
    print("MARKET TRENDS AGENT - LOCAL STREAMING TEST")
    print("=" * 60)
    print(f"\nQuery: {user_query}\n")

    session_id = f"test-local-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    actor_id = "demo-user"
    agent = create_market_trends_agent(session_id, actor_id)

    # Invoke agent with streaming
    handler = LocalStreamingHandler()
    await handler.handle_stream(agent, user_query)

    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys

    # Check for command-line argument (single query mode)
    if len(sys.argv) > 1:
        # Use command-line argument as query
        user_query = " ".join(sys.argv[1:])
        print(f"\nUsing query: {user_query}\n")
        asyncio.run(test_streaming_local(user_query))
    else:
        # Multi-turn interactive chat mode
        asyncio.run(multi_turn_chat())
