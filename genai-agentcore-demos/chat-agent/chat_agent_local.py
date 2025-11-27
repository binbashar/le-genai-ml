#!/usr/bin/env python3
"""
Chat Agent - Local Testing Version

Interactive CLI for testing the LangGraph chat agent without AgentCore Runtime.
Demonstrates:
- Direct LangGraph invocation
- Streaming responses with token-by-token output
- In-memory conversation history (no AgentCore Memory)

Usage:
    uv run python chat_agent_local.py

Press Enter for random example, or type your message.
Type 'quit' or 'exit' to end.
"""

import random

from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

SYSTEM_PROMPT = """You are a helpful AI assistant. Provide clear, concise responses.
You remember previous messages in our conversation and can reference them when relevant."""


def create_chat_graph():
    """Create simple LangGraph with single chat node."""
    llm = ChatBedrock(
        model_id="us.amazon.nova-lite-v1:0",
        model_kwargs={"temperature": 0.7},
    )

    def chat_node(state: MessagesState):
        """Process messages and generate response."""
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("chat", chat_node)
    graph_builder.add_edge(START, "chat")
    graph_builder.add_edge("chat", END)

    return graph_builder.compile()


def stream_chat_response(messages: list) -> str:
    """Stream response token-by-token and return full response."""
    llm_streaming = ChatBedrock(
        model_id="us.amazon.nova-lite-v1:0",
        model_kwargs={"temperature": 0.7},
        streaming=True,
    )

    full_response = ""
    for chunk in llm_streaming.stream(messages):
        if chunk.content:
            # Handle Nova's list-based content blocks
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict) and "text" in block:
                        print(block["text"], end="", flush=True)
                        full_response += block["text"]
            else:
                print(chunk.content, end="", flush=True)
                full_response += chunk.content

    print()  # Newline after streaming
    return full_response


def run_interactive_chat():
    """Run interactive chat session with conversation history."""
    example_prompts = [
        "Hello! How are you today?",
        "What's the capital of France?",
        "Can you explain what an API is in simple terms?",
        "Tell me a fun fact about space.",
        "What are some tips for better sleep?",
        "How does a refrigerator work?",
        "What's the difference between HTTP and HTTPS?",
        "Recommend a book for someone new to programming.",
    ]

    print("\n" + "=" * 60)
    print("CHAT AGENT - LOCAL TESTING")
    print("=" * 60)
    print("\nInteractive chat with conversation memory.")
    print("Press Enter for random prompt, or type your message.")
    print("Type 'quit', 'exit', or 'q' to end.")
    print("Type 'clear' to reset conversation history.")
    print("=" * 60 + "\n")

    # Maintain conversation history
    conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]
    turn_count = 0

    while True:
        # Get user input
        user_input = input("You: ").strip()

        # Handle special commands
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        if user_input.lower() == "clear":
            conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]
            turn_count = 0
            print("\n[Conversation history cleared]\n")
            continue

        # Use random example if empty input
        if not user_input:
            user_input = random.choice(example_prompts)
            print(f"[Using random prompt: {user_input}]")

        turn_count += 1
        print(f"\n--- Turn {turn_count} ---")

        # Add user message to history
        conversation_history.append(HumanMessage(content=user_input))

        # Stream response
        print("\nAssistant: ", end="", flush=True)
        response = stream_chat_response(conversation_history)

        # Add assistant response to history
        conversation_history.append(AIMessage(content=response))

        print()  # Extra newline for readability


def test_single_message(message: str):
    """Test a single message without conversation history (useful for scripts)."""
    print("\n" + "=" * 60)
    print("CHAT AGENT - SINGLE MESSAGE TEST")
    print("=" * 60)
    print(f"\nMessage: {message}\n")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]

    print("Response: ", end="", flush=True)
    response = stream_chat_response(messages)

    print("\n" + "=" * 60 + "\n")
    return response


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Single message mode from command line
        message = " ".join(sys.argv[1:])
        test_single_message(message)
    else:
        # Interactive mode
        run_interactive_chat()
