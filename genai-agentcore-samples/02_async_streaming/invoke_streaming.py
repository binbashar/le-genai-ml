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
        print("   export AGENT_RUNTIME_ARN='arn:aws:bedrock-agentcore:region:account:runtime/name'")
        print("   uv run invoke_streaming.py 'your query'")
        print("\n   Option 2 - Command line argument:")
        print("   uv run invoke_streaming.py 'your query' 'arn:aws:bedrock-agentcore:...'")
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
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        payload=payload
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
                            print(f"Brands: {', '.join(metadata.get('brands', [])) or 'None'}")
                            print(f"Products: {', '.join(metadata.get('products', [])) or 'None'}")
                            print(f"{'─'*60}\n")
                            
                        elif event_type == "error":
                            print(f"\n❌ Error: {event_data.get('message', 'Unknown error')}\n")
                    
                    except json.JSONDecodeError:
                        # If not JSON, print raw line (fallback)
                        print(line)
    
    elif response.get("contentType") == "application/json":
        # Handle standard JSON response
        content = []
        for chunk in response.get("response", []):
            content.append(chunk.decode('utf-8'))
        print(json.loads(''.join(content)))
    
    else:
        # Print raw response for other content types
        print(response)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run invoke_streaming.py 'Your query here' [agent_arn]")
        print("\nExamples:")
        print("  # Using environment variable or .bedrock_agentcore.yaml")
        print("  uv run invoke_streaming.py 'How does AWS Lambda work?'")
        print("\n  # Providing ARN explicitly")
        print("  uv run invoke_streaming.py 'How does AWS Lambda work?' 'arn:aws:bedrock-agentcore:...'")
        print("\n  # Using environment variable")
        print("  export AGENT_RUNTIME_ARN='arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/agent-name'")
        print("  uv run invoke_streaming.py 'How does AWS Lambda work?'")
        sys.exit(1)
    
    # Parse arguments
    query = sys.argv[1]
    agent_arn = sys.argv[2] if len(sys.argv) > 2 else None
    
    invoke_streaming_agent(query, agent_arn)
