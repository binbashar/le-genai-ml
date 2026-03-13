"""
Local testing version of streaming_agent.py
Demonstrates LangGraph parallel node execution with fan-out/fan-in pattern
"""

from langgraph.graph import StateGraph, START, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict
import random


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
        import json

        try:
            keywords = json.loads(response.content)
        except:
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


def test_parallel_execution(user_query: str):
    """
    Test the parallel execution with clean progress updates.
    Final answer streams token-by-token.
    """
    agent = create_streaming_agent()
    llm_streaming = ChatBedrock(
        model_id="us.amazon.nova-micro-v1:0",
        model_kwargs={"temperature": 0.3},
        streaming=True,
    )

    print("\n" + "=" * 60)
    print("LANGGRAPH PARALLEL EXECUTION DEMO")
    print("=" * 60)
    print(f"\nQuery: {user_query}\n")

    initial_state: RequestState = {
        "query": user_query,
        "category": None,
        "keywords": None,
    }

    # Show progress
    print("🔄 Classifying request...")
    print("🔍 Detecting keywords...")
    print()

    # Execute parallel nodes
    final_state = agent.invoke(initial_state)

    # Show intermediate results
    print(f"✓ Request classified as: {final_state['category']}")
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
    print(f"✓ Keywords detected: Brands={brands}, Products={products}")
    print()

    # Stream the final answer
    print("💬 Answer (streaming):\n")

    # Build context for streaming answer
    context_parts = [
        f"Question Category: {final_state['category']}",
        f"Detected Brands: {brands}",
        f"Detected Products: {products}",
    ]
    context = "\n".join(context_parts)

    system_msg = SystemMessage(
        content=f"""You are a helpful AI assistant. Answer the user's question based on this context:

{context}

Provide a helpful response (5-6 sentences) that directly addresses their question. Use markdown formatting to make the response more readable."""
    )

    # Stream token by token
    for chunk in llm_streaming.stream([system_msg, HumanMessage(content=user_query)]):
        if chunk.content:
            # Handle Nova Micro's list-based content blocks
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict) and "text" in block:
                        print(block["text"], end="", flush=True)
            else:
                # Fallback for string-based content
                print(chunk.content, end="", flush=True)

    print("\n\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Example queries for random selection (with rich keywords)
    example_queries = [
        "I'm having issues with AWS Lambda timeouts when using Bedrock models. Can you help?",
        "What are the best practices for using Amazon S3 with CloudFront CDN?",
        "How can I optimize costs when running multiple EC2 instances with Auto Scaling?",
        "I need help integrating AWS Cognito with our React application hosted on Amplify",
        "Suggest improvements for our DynamoDB table that connects to Lambda and API Gateway",
        "Explain the differences between AWS Fargate and ECS on EC2 for Docker containers",
        "Can you help me set up a data pipeline using AWS Glue, Athena, and Redshift?",
        "What's the best way to deploy a Next.js application on AWS using CloudFront and S3?",
    ]

    print("\n" + "=" * 60)
    print("LANGGRAPH PARALLEL EXECUTION - INTERACTIVE DEMO")
    print("=" * 60)
    print("\nEnter your query (Enter for random example):")
    print()

    user_input = input("> ").strip()

    if not user_input:
        user_query = random.choice(example_queries)
        print(f"[Selected random query: {user_query}]\n")
    else:
        user_query = user_input

    # Run parallel execution demo (one-shot)
    test_parallel_execution(user_query)
