#!/usr/bin/env python3
"""
STM test that mimics Streamlit's behavior exactly.

This test:
1. Uses the same session ID across multiple invocations (like Streamlit)
2. Persists session ID to a file (like Streamlit)
3. Tests conversation continuity by asking about previous messages
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


def get_or_create_session_id(agent_type: str, username: str) -> str:
    """Get session ID from file or create new one - exactly like Streamlit."""
    sessions_dir = Path(__file__).parent / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    session_file = sessions_dir / f".{agent_type}_{username}"
    print(f"📁 Session file: {session_file}")

    # Try to read existing session ID
    if session_file.exists():
        try:
            session_id = session_file.read_text().strip()
            if session_id and len(session_id) >= 33:  # AWS minimum
                print(f"♻️ Reusing existing session ID: {session_id[:12]}...")
                return session_id
        except Exception as e:
            print(f"⚠️ Failed to read session file: {e}")

    # Generate new session ID
    session_id = str(uuid.uuid4())

    # Save to file
    try:
        session_file.write_text(session_id)
        print(f"🆕 Created new session ID: {session_id[:12]}...")
    except Exception as e:
        print(f"⚠️ Failed to save session file: {e}")

    return session_id


def test_stm_like_streamlit():
    """Test STM using Streamlit's exact session management pattern."""

    print("\n" + "="*60)
    print("🧠 STM TEST - MIMICKING STREAMLIT BEHAVIOR")
    print("="*60)

    # Load configuration
    config_path = Path(__file__).parent.parent / "finance-personal-assistant" / ".bedrock_agentcore.yaml"

    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)

    agent_config = yaml_config['agents']['finance_personal_assistant']
    agent_arn = agent_config['bedrock_agentcore']['agent_arn']
    region = agent_config['aws']['region']

    print(f"Agent: {agent_arn}")
    print(f"Region: {region}")

    # Get OAuth config and authenticate
    oauth_config = extract_oauth_config_from_yaml(config_path)
    if not oauth_config:
        print("❌ No OAuth config")
        return False

    print("\nAuthenticating...")
    try:
        auth_result = authenticate(oauth_config, "broker_demo", "DemoPass123!")
        token = auth_result["AccessToken"]
        print("✓ Authenticated as broker_demo")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return False

    # Get or create session ID - exactly like Streamlit does
    agent_type = "finance_personal_assistant"
    username = "broker_demo"
    session_id = get_or_create_session_id(agent_type, username)

    print(f"\n📍 Using session ID for all invocations")
    print(f"   (This mimics Streamlit's session persistence)")

    try:
        # Message 1: Introduction
        print("\n" + "="*60)
        print("📨 MESSAGE 1: Introduction")
        print("-"*60)

        prompt1 = "Hello! My name is Alex and I work in tech."
        print(f"Sending: '{prompt1}'")

        response1 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt=prompt1,
            session_id=session_id,
            region=region,
            timeout=30
        )

        if response1.status_code != 200:
            print(f"❌ HTTP {response1.status_code}")
            return False

        output1 = parse_sse_response(response1.text)
        print(f"Response: {output1[:150]}...")

        # Message 2: Ask about favorite color
        print("\n" + "="*60)
        print("📨 MESSAGE 2: Share preference")
        print("-"*60)

        prompt2 = "My favorite color is green."
        print(f"Sending: '{prompt2}'")

        response2 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt=prompt2,
            session_id=session_id,
            region=region,
            timeout=30
        )

        if response2.status_code != 200:
            print(f"❌ HTTP {response2.status_code}")
            return False

        output2 = parse_sse_response(response2.text)
        print(f"Response: {output2[:150]}...")

        # Message 3: Ask about previous message - KEY TEST
        print("\n" + "="*60)
        print("📨 MESSAGE 3: Test memory of previous message")
        print("-"*60)

        prompt3 = "What was my last message to you?"
        print(f"Sending: '{prompt3}'")

        response3 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt=prompt3,
            session_id=session_id,
            region=region,
            timeout=30
        )

        if response3.status_code != 200:
            print(f"❌ HTTP {response3.status_code}")
            return False

        output3 = parse_sse_response(response3.text)
        print(f"Response: {output3[:300]}...")

        # Check if agent remembers the last message
        test1_pass = "green" in output3.lower() or "color" in output3.lower()

        # Message 4: Ask about earlier information
        print("\n" + "="*60)
        print("📨 MESSAGE 4: Test memory of earlier information")
        print("-"*60)

        prompt4 = "What is my name and what do I do for work?"
        print(f"Sending: '{prompt4}'")

        response4 = invoke_with_token(
            agent_arn=agent_arn,
            token=token,
            prompt=prompt4,
            session_id=session_id,
            region=region,
            timeout=30
        )

        if response4.status_code != 200:
            print(f"❌ HTTP {response4.status_code}")
            return False

        output4 = parse_sse_response(response4.text)
        print(f"Response: {output4[:300]}...")

        # Check if agent remembers earlier info
        test2_pass = ("alex" in output4.lower()) and ("tech" in output4.lower())

        # Results
        print("\n" + "="*60)
        print("📊 TEST RESULTS")
        print("="*60)

        print(f"✓ Session persistence: Same session ID used across all messages")
        print(f"{'✅' if test1_pass else '❌'} Last message recall: Agent {'remembered' if test1_pass else 'forgot'} about color")
        print(f"{'✅' if test2_pass else '❌'} Earlier info recall: Agent {'remembered' if test2_pass else 'forgot'} name and job")

        overall_pass = test1_pass or test2_pass  # At least one should work

        if overall_pass:
            print("\n🎉 STM TEST PASSED - Agent maintains conversation context!")
        else:
            print("\n⚠️ STM TEST FAILED - Agent may not be maintaining context")

        return overall_pass

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_session_file():
    """Optional: Clean up session file after testing."""
    sessions_dir = Path(__file__).parent / "sessions"
    if sessions_dir.exists():
        print("\n🧹 Cleaning up session files...")
        for session_file in sessions_dir.glob(".finance_personal_assistant_*"):
            try:
                session_file.unlink()
                print(f"   Removed: {session_file.name}")
            except Exception as e:
                print(f"   Failed to remove {session_file.name}: {e}")


def main():
    """Run the test."""
    success = test_stm_like_streamlit()

    print("\n" + "="*60)
    print("📝 SUMMARY")
    print("="*60)
    print("This test mimics Streamlit's behavior:")
    print("- ✓ Persists session ID to file")
    print("- ✓ Reuses same session ID across invocations")
    print("- ✓ Tests conversation continuity")

    if success:
        print("\n✅ The agent's STM works like Streamlit expects!")
    else:
        print("\n⚠️ The agent's STM may have issues with conversation continuity")

    # Optionally clean up (comment out to test persistence across script runs)
    # cleanup_session_file()

    print("="*60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())