#!/usr/bin/env python3
"""
Final working memory test - ensures proper session ID length and SSE parsing.
Based on health check and auth_utils requirements.
"""

import json
import sys
import uuid
from pathlib import Path

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
                # Try to parse as JSON string
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


def test_memory():
    """Test memory with proper session handling."""

    print("\n" + "="*60)
    print("🧠 FINAL MEMORY TEST")
    print("="*60)

    # Load config
    config_path = Path(__file__).parent.parent / "finance-personal-assistant" / ".bedrock_agentcore.yaml"

    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)

    agent_config = yaml_config['agents']['finance_personal_assistant']
    agent_arn = agent_config['bedrock_agentcore']['agent_arn']
    region = agent_config['aws']['region']

    print(f"Agent ARN: {agent_arn}")
    print(f"Region: {region}")

    # Get OAuth config
    oauth_config = extract_oauth_config_from_yaml(config_path)

    if not oauth_config:
        print("❌ No OAuth config")
        return False

    print("✓ OAuth config loaded")

    # Authenticate
    print("\nAuthenticating...")

    try:
        auth_result = authenticate(oauth_config, "broker_demo", "DemoPass123!")
        token = auth_result["AccessToken"]
        print("✓ Authenticated as broker_demo")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return False

    # Generate session ID that meets AWS requirements (>= 33 chars)
    # invoke_with_token will auto-extend if needed, but let's be explicit
    session_base = f"memory-test-{uuid.uuid4().hex}"
    session_id = f"{session_base}-{uuid.uuid4()}" if len(session_base) < 33 else session_base

    print(f"\nSession ID: {session_id}")
    print(f"Session length: {len(session_id)} chars (AWS requires >= 33)")

    try:
        # Test 1: Simple fact
        print("\n📝 TEST: Simple fact memory")
        print("-"*40)

        # Teach
        print("Teaching: 'My lucky number is 7'")

        response1 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt="My lucky number is 7. Remember this important fact about me.",
            session_id=session_id,
            region=region,
            timeout=30
        )

        if response1.status_code != 200:
            print(f"❌ HTTP {response1.status_code}")
            return False

        output1 = parse_sse_response(response1.text)
        print(f"Response: {output1[:100]}...")

        # Recall
        print("\nRecalling: 'What is my lucky number?'")

        response2 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt="What is my lucky number?",
            session_id=session_id,
            region=region,
            timeout=30
        )

        if response2.status_code != 200:
            print(f"❌ HTTP {response2.status_code}")
            return False

        output2 = parse_sse_response(response2.text)
        print(f"Response: {output2[:200]}...")

        # Check
        if "7" in output2 or "seven" in output2.lower():
            print("✅ Agent remembered the number!")
            memory_works = True
        else:
            print("❌ Agent didn't remember the number")
            memory_works = False

        # Test 2: Session isolation (different session should NOT remember)
        print("\n🔒 TEST: Session isolation")
        print("-"*40)

        new_session = f"isolation-test-{uuid.uuid4()}"
        print(f"New session: {new_session}")
        print("Asking same question in new session...")

        response3 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt="What is my lucky number?",
            session_id=new_session,
            region=region,
            timeout=30
        )

        if response3.status_code != 200:
            print(f"❌ HTTP {response3.status_code}")
        else:
            output3 = parse_sse_response(response3.text)
            print(f"Response: {output3[:200]}...")

            if "7" not in output3 and "seven" not in output3.lower():
                print("✅ New session correctly doesn't know the number")
            else:
                print("⚠️ New session somehow knows the number (possible LTM)")

        return memory_works

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    success = test_memory()

    print("\n" + "="*60)
    if success:
        print("🎉 MEMORY TEST PASSED!")
        print("The agent successfully remembered information within the session.")
    else:
        print("⚠️ MEMORY TEST FAILED")
        print("\nPossible reasons:")
        print("- Agent might not have memory enabled in deployment")
        print("- Session management might need different configuration")
        print("- Try checking agent's memory mode in .bedrock_agentcore.yaml")
    print("="*60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())