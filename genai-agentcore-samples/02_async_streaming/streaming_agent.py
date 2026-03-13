"""
AgentCore Runtime streaming agent with parallel node execution.

This demonstrates:
1. Parallel node execution (fan-out/fan-in pattern)
2. Streaming progress updates to users
3. Real-time insights as processing happens
"""

from langgraph.graph import StateGraph, START, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from typing import TypedDict
import json
import asyncio

app = BedrockAgentCoreApp()


class RequestState(TypedDict):
    """State that tracks the request processing pipeline"""

    query: str
    category: str | None
    keywords: dict | None


def create_streaming_agent():
    """
    Create a parallel processing agent that demonstrates fan-out/fan-in.

    Graph structure:
                    ┌─> classify_request ──┐
        START ──────┤                       ├──> END
                    └─> extract_keywords ──┘

    This showcases:
    1. Parallel execution (classify and extract run simultaneously)
    2. Clean, minimalist approach
    3. Results used for context-aware streaming response
    """
    llm = ChatBedrock(
        model_id="us.amazon.nova-micro-v1:0",
        model_kwargs={"temperature": 0.3},
    )

    def classify_request(state: RequestState):
        """Classify user request into one of three categories"""
        system_msg = SystemMessage(
            content="""Classify the user request into EXACTLY ONE category:
            - inquiry: Questions or information requests
            - complaint: Technical issues or problems to solve
            - feedback: Suggestions or improvement ideas

            Return ONLY the category name, nothing else."""
        )

        response = llm.invoke([system_msg, HumanMessage(content=state["query"])])

        return {"category": response.content.strip().lower()}

    def extract_keywords(state: RequestState):
        """Extract relevant entities: brands, products, and people"""
        system_msg = SystemMessage(
            content="""Extract entities from the text and return as JSON:
            {
              "brands": ["list of brand names like AWS, Google, Microsoft"],
              "products": ["list of product names like Lambda, Bedrock, S3"],
              "people": ["list of people names if mentioned"]
            }

            Return ONLY the JSON object, nothing else."""
        )

        response = llm.invoke([system_msg, HumanMessage(content=state["query"])])

        # Parse JSON response
        try:
            keywords = json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            keywords = {"brands": [], "products": [], "people": []}

        return {"keywords": keywords}

    # Build graph with parallel execution
    graph_builder = StateGraph(RequestState)

    # Add parallel nodes
    graph_builder.add_node("classify_request", classify_request)
    graph_builder.add_node("extract_keywords", extract_keywords)

    # Fan-out: START branches to two parallel nodes
    graph_builder.add_edge(START, "classify_request")
    graph_builder.add_edge(START, "extract_keywords")

    # Both nodes go to END
    graph_builder.add_edge("classify_request", END)
    graph_builder.add_edge("extract_keywords", END)

    return graph_builder.compile()


# Initialize the agent
agent = create_streaming_agent()


@app.entrypoint
async def analyze_with_streaming(payload, context):
    """
    Entrypoint demonstrating AgentCore's streaming capabilities:
    1. Partial responses (thinking messages) during parallel execution
    2. Token-by-token streaming of final answer

    This replicates the local version's behavior with AgentCore runtime.
    IMPORTANT: Must be async for real-time streaming to work.

    Args:
        payload: Dict with 'query' key containing user request
        context: AgentCore context object

    Yields:
        Dict with 'type' and data about progress/results/tokens
    """
    user_query = payload.get("query", "")

    if not user_query:
        yield {
            "type": "error",
            "message": "No query provided. Please include 'query' in payload.",
        }
        return

    # Initialize state
    initial_state: RequestState = {
        "query": user_query,
        "category": None,
        "keywords": None,
    }

    # Show thinking messages during parallel execution
    yield {"type": "thinking", "message": "🔄 Classifying request..."}

    yield {"type": "thinking", "message": "🔍 Detecting keywords..."}

    # Execute parallel nodes (async wrapper for blocking call)
    final_state = await asyncio.to_thread(agent.invoke, initial_state)

    # Show intermediate results
    brands = (
        ", ".join(final_state["keywords"]["brands"])
        if final_state["keywords"]["brands"]
        else "None"
    )
    products = (
        ", ".join(final_state["keywords"]["products"])
        if final_state["keywords"]["products"]
        else "None"
    )

    yield {
        "type": "thinking",
        "message": f"✓ Request classified as: {final_state['category']}",
    }

    yield {
        "type": "thinking",
        "message": f"✓ Keywords detected: Brands={brands}, Products={products}",
    }

    yield {"type": "thinking", "message": "💬 Streaming answer..."}

    # Build context for streaming answer
    context_parts = [
        f"Question Category: {final_state['category']}",
        f"Detected Brands: {brands}",
        f"Detected Products: {products}",
    ]
    context_info = "\n".join(context_parts)

    # Stream the final answer token by token
    llm_streaming = ChatBedrock(
        model_id="us.amazon.nova-micro-v1:0",
        model_kwargs={"temperature": 0.3},
        streaming=True,
    )

    system_msg = SystemMessage(
        content=f"""You are a helpful AI assistant. Answer the user's question based on this context:

{context_info}

Provide a helpful response (5-6 sentences) that directly addresses their question. Use markdown formatting to make the response more readable."""
    )

    # Stream tokens as they're generated (using async stream)
    full_response = ""

    # Use astream for true async streaming
    async for chunk in llm_streaming.astream(
        [system_msg, HumanMessage(content=user_query)]
    ):
        if chunk.content:
            # Handle Nova Micro's list-based content blocks
            token_text = ""
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict) and "text" in block:
                        token_text += block["text"]
            else:
                # Fallback for string-based content
                token_text = chunk.content

            full_response += token_text
            yield {
                "type": "stream_token",
                "token": token_text,
                "accumulated": full_response,
            }

    # Signal completion
    yield {
        "type": "final",
        "result": full_response,
        "metadata": {
            "category": final_state["category"],
            "brands": final_state["keywords"]["brands"],
            "products": final_state["keywords"]["products"],
        },
    }


if __name__ == "__main__":
    app.run()
