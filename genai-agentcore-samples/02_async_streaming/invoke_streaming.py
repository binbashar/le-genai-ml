"""
Invoke AgentCore Runtime with real-time streaming output.

Based on official AWS Bedrock AgentCore documentation:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html

Uses the invoke_agent_runtime API with text/event-stream response processing.
"""
import boto3
import json
import sys
import uuid
import os
import random


def get_agent_arn() -> str | None:
    """
    Get agent ARN from environment variable.

    Returns:
        Agent ARN or None if not found
    """
    return os.environ.get("AGENT_RUNTIME_ARN")


def invoke_streaming_agent(query: str, agent_arn: str | None = None):
    """
    Invoke the streaming agent and display results in real-time.

    Implementation follows AWS documentation pattern for processing
    text/event-stream responses from AgentCore Runtime.

    Args:
        query: User query to process
        agent_arn: Optional ARN of the AgentCore runtime (if not provided, reads from env/config)
    """
    # Initialize the Bedrock AgentCore client
    agent_core_client = boto3.client("bedrock-agentcore")

    # Get agent ARN
    if not agent_arn:
        agent_arn = get_agent_arn()

    if not agent_arn:
        print("❌ Agent ARN not found. Please provide it via:")
        print("\n   Option 1 - Environment variable:")
        print(
            "   export AGENT_RUNTIME_ARN='arn:aws:bedrock-agentcore:region:account:runtime/name'"
        )
        print("   uv run invoke_streaming.py 'your query'")
        print("\n   Option 2 - Command line argument:")
        print(
            "   uv run invoke_streaming.py 'your query' 'arn:aws:bedrock-agentcore:...'"
        )
        print("\n   Get your ARN from: agentcore status")
        return

    print(f"\n{'='*60}")
    print("AGENTCORE STREAMING DEMO")
    print(f"{'='*60}")
    print(f"\nQuery: {query}\n")

    # Generate unique session ID (as recommended in AWS docs)
    session_id = str(uuid.uuid4())

    # Prepare the payload
    payload = json.dumps({"query": query}).encode()

    # Invoke the agent
    response = agent_core_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn, runtimeSessionId=session_id, payload=payload
    )

    # Process and print the response using event-stream.
    if "text/event-stream" in response.get("contentType", ""):
        for line in response["response"].iter_lines(chunk_size=10):
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]

                    # Parse and display streaming events
                    try:
                        event_data = json.loads(line)
                        event_type = event_data.get("type")

                        if event_type == "thinking":
                            # Show thinking messages immediately
                            print(event_data.get("message", ""))

                        elif event_type == "stream_token":
                            # Stream tokens in real-time
                            token = event_data.get("token", "")
                            print(token, end="", flush=True)

                        elif event_type == "final":
                            # Show final results
                            print("\n")
                            metadata = event_data.get("metadata", {})
                            print(f"\n{'─'*60}")
                            print(f"Category: {metadata.get('category', 'N/A')}")
                            print(
                                f"Brands: {', '.join(metadata.get('brands', [])) or 'None'}"
                            )
                            print(
                                f"Products: {', '.join(metadata.get('products', [])) or 'None'}"
                            )
                            print(f"{'─'*60}\n")

                        elif event_type == "error":
                            print(
                                f"\n❌ Error: {event_data.get('message', 'Unknown error')}\n"
                            )

                    except json.JSONDecodeError:
                        # If not JSON, print raw line (fallback)
                        print(line)

    elif response.get("contentType") == "application/json":
        # Handle standard JSON response
        content = []
        for chunk in response.get("response", []):
            content.append(chunk.decode("utf-8"))
        print(json.loads("".join(content)))

    else:
        # Print raw response for other content types
        print(response)


if __name__ == "__main__":
    # Example queries for random selection
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
    print("AGENTCORE RUNTIME - INTERACTIVE STREAMING DEMO")
    print("=" * 60)
    print()

    # Get agent ARN from environment or prompt user
    agent_arn = get_agent_arn()

    if not agent_arn:
        print("Agent ARN not found in environment variables.")
        print("\nYou can get your ARN from: agentcore status")
        print("Or find it in AWS Console: Bedrock > AgentCore > Runtimes\n")
        agent_arn = input("Enter Agent Runtime ARN (or press Enter to exit): ").strip()

        if not agent_arn:
            print("\nExiting. To set ARN automatically, use:")
            print(
                "  export AGENT_RUNTIME_ARN='arn:aws:bedrock-agentcore:region:account:runtime/name'"
            )
            sys.exit(0)
    else:
        print(f"Using Agent ARN: {agent_arn[:60]}...")
        print()

    # Get user query
    print("Enter your query (or press Enter for random example):")
    print()
    user_input = input("> ").strip()

    if not user_input:
        query = random.choice(example_queries)
        print(f"\n[Selected random query: {query}]\n")
    else:
        query = user_input

    # Invoke the streaming agent
    invoke_streaming_agent(query, agent_arn)
