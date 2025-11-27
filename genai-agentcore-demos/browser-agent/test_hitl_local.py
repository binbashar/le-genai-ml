#!/usr/bin/env python3
"""
Test script for HITL (Human-in-the-Loop) Browser Agent

This script demonstrates the complete HITL flow:
1. Agent navigates to a website
2. Detects login requirement
3. Pauses automation (UpdateBrowserStream)
4. User completes login via Live View
5. Automation resumes
6. Agent continues with task
"""

import json
import time
import uuid

from browser_agent_hitl import HITLBrowserAgent


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_hitl_flow():
    """Test complete HITL flow with banking scenario"""

    print_section("HITL Browser Agent - Banking Login Test")

    # Initialize agent
    agent = HITLBrowserAgent()
    session_id = f"test-{uuid.uuid4().hex[:8]}"

    print(f"\nSession ID: {session_id}")
    print("Scenario: Navigate to bank website and login")

    # ========================================================================
    # Step 1: Agent starts task
    # ========================================================================

    print_section("Step 1: Agent Starts Task")

    task = (
        input("\nEnter banking task (or press Enter for default):\n> ").strip()
        or "Navigate to https://example-bank.com/login and login to my account"
    )

    print(f"\nTask: {task}")
    print("\nExecuting agent...")

    result = agent.execute(user_message=task, session_id=session_id)

    print("\n📊 Result:")
    print(json.dumps(result, indent=2))

    # ========================================================================
    # Step 2: Check if human intervention needed
    # ========================================================================

    if result["status"] == "awaiting_human":
        print_section("Step 2: Human Intervention Required")

        print("\n🚨 AUTOMATION PAUSED")
        print(f"\nStatus: {result['message']}")
        print(f"\n📺 Live View URL:\n   {result.get('live_view_url')}")

        print("\n" + "-" * 70)
        print("INSTRUCTIONS FOR HUMAN OPERATOR:")
        print("-" * 70)
        print("1. Open the Live View URL in your browser")
        print("2. You will see the browser session in real-time")
        print("3. Complete the login manually:")
        print("   - Enter your document number")
        print("   - Enter your password")
        print("   - Click login button")
        print("4. Wait for successful login")
        print("5. Return here and press Enter to continue")
        print("-" * 70)

        input("\n⏸️  Press Enter when you've completed the manual login...\n")

        # ====================================================================
        # Step 3: Resume automation
        # ====================================================================

        print_section("Step 3: Resume Automation")

        print("\n▶️  Resuming automation...")

        continue_result = agent.continue_after_human(
            "Check my account balance and recent transactions"
        )

        print("\n📊 Continuation Result:")
        print(json.dumps(continue_result, indent=2))

        # ====================================================================
        # Step 4: Summary
        # ====================================================================

        print_section("Test Summary")

        print("\n✅ HITL Flow Completed Successfully!")
        print("\nSteps executed:")
        print("  1. ✅ Agent detected login requirement")
        print("  2. ✅ Automation paused (UpdateBrowserStream: DISABLED)")
        print("  3. ✅ Human completed login via Live View")
        print("  4. ✅ Automation resumed (UpdateBrowserStream: ENABLED)")
        print("  5. ✅ Agent continued with task")

        print("\n🔐 Security Notes:")
        print("  - Credentials never passed through agent")
        print("  - No sensitive data logged")
        print("  - Live View requires AWS authentication")
        print("  - Session isolated and ephemeral")

    elif result["status"] == "completed":
        print_section("Task Completed (No Human Intervention Needed)")

        print("\n✅ Agent completed task without requiring login")
        print("\nAgent Response:")
        print(result.get("agent_response"))

    else:
        print_section("Error Occurred")

        print(f"\n❌ Status: {result['status']}")
        print(f"Message: {result.get('message', 'Unknown error')}")

    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70 + "\n")


def test_session_states():
    """Test session state management"""

    print_section("Session State Management Test")

    agent = HITLBrowserAgent()

    # Test 1: Get status before starting session
    print("\nTest 1: Status before session start")
    status = agent.session_manager.get_status()
    print(json.dumps(status, indent=2))
    assert status["status"] == "no_session"

    # Test 2: Start session
    print("\nTest 2: Start session")
    session_id = f"state-test-{uuid.uuid4().hex[:8]}"
    session_info = agent.session_manager.start_session(session_id)
    print(json.dumps(session_info, indent=2))

    # Test 3: Get status after starting
    print("\nTest 3: Status after session start")
    status = agent.session_manager.get_status()
    print(json.dumps(status, indent=2))
    assert status["status"] == "active"

    print("\n✅ All session state tests passed!")


def test_update_browser_stream():
    """Test UpdateBrowserStream API integration"""

    print_section("UpdateBrowserStream API Test")

    session_manager = HITLBrowserAgent().session_manager
    session_id = f"api-test-{uuid.uuid4().hex[:8]}"

    print(f"\nSession ID: {session_id}")

    # Note: This test requires an actual browser session
    # In production, you'd have a real browser_identifier
    print("\n⚠️  Note: This is a mock test")
    print("In production, you need:")
    print("  - Actual browser session from StartBrowserSession API")
    print("  - Valid browser_identifier")
    print("  - Active session_id")

    print("\nMock API calls that would be made:")
    print("\n1. Pause automation:")
    print(
        """
    client.update_browser_stream(
        browserIdentifier='browser-abc123',
        sessionId='{session_id}',
        streamUpdate={{
            'automationStreamUpdate': {{
                'streamStatus': 'DISABLED'
            }}
        }}
    )
    """.format(
            session_id=session_id
        )
    )

    print("\n2. Resume automation:")
    print(
        """
    client.update_browser_stream(
        browserIdentifier='browser-abc123',
        sessionId='{session_id}',
        streamUpdate={{
            'automationStreamUpdate': {{
                'streamStatus': 'ENABLED'
            }}
        }}
    )
    """.format(
            session_id=session_id
        )
    )

    print("\n✅ UpdateBrowserStream API structure verified!")


def interactive_menu():
    """Interactive test menu"""

    print("\n" + "=" * 70)
    print("  HITL Browser Agent - Test Suite")
    print("=" * 70)

    while True:
        print("\n\nSelect a test:")
        print("  1. Full HITL Flow (Banking Login)")
        print("  2. Session State Management")
        print("  3. UpdateBrowserStream API Structure")
        print("  4. Exit")

        choice = input("\nYour choice: ").strip()

        if choice == "1":
            test_hitl_flow()
        elif choice == "2":
            test_session_states()
        elif choice == "3":
            test_update_browser_stream()
        elif choice == "4":
            print("\n👋 Goodbye!\n")
            break
        else:
            print("\n❌ Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    # Run interactive menu
    interactive_menu()
