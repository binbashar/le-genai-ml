#!/usr/bin/env python3
"""
Generate test interactions with the chat agent to populate CloudWatch logs.
This will trigger the Firehose pipeline for evaluation testing.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

import boto3
from botocore.config import Config

# Add parent directory to path for libs module
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_region


def get_agent_arn() -> str:
    """Extract agent ARN from .bedrock_agentcore.yaml"""
    yaml_path = Path(__file__).parent / ".bedrock_agentcore.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")

    with open(yaml_path) as f:
        for line in f:
            if "agent_arn:" in line:
                return line.split("agent_arn:")[1].strip()

    raise ValueError("agent_arn not found in .bedrock_agentcore.yaml")


def create_client(region: str):
    """Create Bedrock AgentCore client"""
    config = Config(
        region_name=region,
        retries={"max_attempts": 3, "mode": "standard"},
        read_timeout=120,
    )
    return boto3.client("bedrock-agentcore", config=config)


async def invoke_agent(client, agent_arn: str, prompt: str, session_id: str) -> dict:
    """Invoke agent with a prompt and return response"""
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": "test_user",
    }

    print(f"\n{'='*80}")
    print(f"Prompt: {prompt}")
    print(f"Session: {session_id}")
    print(f"{'='*80}")

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            payload=json.dumps(payload),
        )

        # Process streaming response
        response_stream = response.get("response")
        if not response_stream:
            print("❌ No response stream received")
            return {
                "status": "error",
                "error": "No response stream",
                "session_id": session_id,
            }

        full_response = ""
        thinking_msgs = []

        for line in response_stream.iter_lines():
            line_str = line.decode("utf-8") if isinstance(line, bytes) else line
            if line_str.startswith("data: "):
                data_str = line_str[6:].strip()
                try:
                    event = json.loads(data_str)
                    if event.get("type") == "stream_token":
                        token = event.get("token", "")
                        full_response += token
                        print(token, end="", flush=True)
                    elif event.get("type") == "thinking":
                        thinking_msgs.append(event.get("message", ""))
                    elif event.get("type") == "error":
                        print(f"\n❌ Agent error: {event.get('message')}")
                        return {
                            "status": "error",
                            "error": event.get("message"),
                            "session_id": session_id,
                        }
                except json.JSONDecodeError:
                    continue

        print("\n")
        return {
            "status": "success",
            "response": full_response,
            "thinking": thinking_msgs,
            "session_id": session_id,
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"status": "error", "error": str(e), "session_id": session_id}


async def run_test_interactions():
    """Run multiple test interactions to generate CloudWatch logs"""

    # Test prompts covering different scenarios
    test_prompts = [
        "Hello! What's the capital of France?",
        "Can you explain what machine learning is in simple terms?",
        "Tell me a short joke about programming.",
        "What are the benefits of using AWS for cloud computing?",
        "How do I make a good cup of coffee?",
        "What's the difference between Python and JavaScript?",
        "Can you recommend a good book about artificial intelligence?",
        "What are some tips for staying productive while working from home?",
        "Explain quantum computing like I'm five years old.",
        "What's the best way to learn a new programming language?",
    ]

    region = get_region()
    agent_arn = get_agent_arn()

    print(f"\n🚀 Starting test interactions")
    print(f"Region: {region}")
    print(f"Agent ARN: {agent_arn}")
    print(f"Number of prompts: {len(test_prompts)}")

    client = create_client(region)

    # Use same session for continuity testing
    session_id = str(uuid.uuid4())
    results = []

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📝 Interaction {i}/{len(test_prompts)}")
        result = await invoke_agent(client, agent_arn, prompt, session_id)
        results.append(result)

        # Small delay between requests
        if i < len(test_prompts):
            await asyncio.sleep(2)

    # Summary
    print(f"\n{'='*80}")
    print("📊 Summary")
    print(f"{'='*80}")
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"🔑 Session ID: {session_id}")
    print(f"\n💡 These interactions should now appear in CloudWatch logs.")
    print(f"   Check: /aws/bedrock/modelinvocations")
    print(f"   Agent: chat_agent")


if __name__ == "__main__":
    asyncio.run(run_test_interactions())
