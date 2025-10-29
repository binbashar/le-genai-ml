#!/usr/bin/env python3
"""
Simple STM conversation test - demonstrates memory across invocations.

Run this multiple times to see how the agent remembers previous conversations
when using the same session ID (like Streamlit does).
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from shared.auth_utils import authenticate, extract_oauth_config_from_yaml, invoke_with_token


def parse_sse_response(response_text: str) -> str:
    """Parse SSE response to extract text content."""
    if not response_text.startswith("data:"):
        return response_text

    lines = response_text.strip().split("\n")
    content = []

    for line in lines:
        if line.startswith("data: "):
            data_str = line[6:]
            try:
                if data_str.startswith('"') and data_str.endswith('"'):
                    content.append(json.loads(data_str))
                else:
                    event = json.loads(data_str)
                    if isinstance(event, str):
                        content.append(event)
                    elif isinstance(event, dict) and "token" in event:
                        content.append(event["token"])
            except (json.JSONDecodeError, TypeError):
                if data_str and data_str != "[DONE]":
                    content.append(data_str)

    return "".join(content)


def get_persistent_session_id() -> str:
    """Get or create a persistent session ID that survives across runs."""
    session_file = Path(__file__).parent / "sessions" / ".stm_test_session"
    session_file.parent.mkdir(exist_ok=True)

    if session_file.exists():
        session_id = session_file.read_text().strip()
        print(f"♻️ Using existing session: {session_id[:12]}...")
        return session_id

    # Create new session
    import uuid
    session_id = str(uuid.uuid4())
    session_file.write_text(session_id)
    print(f"🆕 Created new session: {session_id[:12]}...")
    return session_id


def have_conversation():
    """Have a single exchange with the agent using persistent session."""

    print("\n" + "="*60)
    print(f"💬 STM CONVERSATION TEST - {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)

    # Load config
    config_path = Path(__file__).parent.parent / "finance-personal-assistant" / ".bedrock_agentcore.yaml"
    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)

    agent_config = yaml_config['agents']['finance_personal_assistant']
    agent_arn = agent_config['bedrock_agentcore']['agent_arn']
    region = agent_config['aws']['region']

    # Authenticate
    oauth_config = extract_oauth_config_from_yaml(config_path)
    auth_result = authenticate(oauth_config, "broker_demo", "DemoPass123!")
    token = auth_result["AccessToken"]

    # Get persistent session
    session_id = get_persistent_session_id()

    # Ask what the agent remembers
    print("\n🤔 Asking: 'What was my last message to you?'")

    response = invoke_with_token(
        agent_arn=agent_arn,
        token=token,
        prompt="What was my last message to you?",
        session_id=session_id,
        region=region,
        timeout=30
    )

    if response.status_code == 200:
        output = parse_sse_response(response.text)
        print(f"🤖 Agent: {output[:200]}...")
    else:
        print(f"❌ Error: HTTP {response.status_code}")
        return

    # Send a new fact
    import random
    facts = [
        f"The current time is {datetime.now().strftime('%H:%M')}",
        f"Today is {datetime.now().strftime('%A')}",
        f"My favorite number is {random.randint(1, 100)}",
        f"I'm thinking about buying {'AAPL' if random.random() > 0.5 else 'GOOGL'} stock",
        "I just had coffee",
        "I'm planning a vacation",
    ]

    new_fact = random.choice(facts)
    print(f"\n📝 Sending: '{new_fact}'")

    response2 = invoke_with_token(
        agent_arn=agent_arn,
        token=token,
        prompt=new_fact,
        session_id=session_id,
        region=region,
        timeout=30
    )

    if response2.status_code == 200:
        output2 = parse_sse_response(response2.text)
        print(f"🤖 Agent: {output2[:200]}...")
    else:
        print(f"❌ Error: HTTP {response2.status_code}")

    print("\n" + "-"*60)
    print("💡 Run this script again to see if the agent remembers this conversation!")
    print("   The session persists across script runs, just like in Streamlit.")


def main():
    """Run the conversation test."""
    try:
        have_conversation()
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())