#!/usr/bin/env python3
"""
Memory Reset Utility

Deletes and recreates the memory instance to ensure complete data clearing.
"""

import os
import sys

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from config import get_region
from session_manager import SESSIONS_FILE, delete_all_sessions


def main():
    print("Memory Reset")
    print("─" * 50)
    print()

    # Get memory details
    region = get_region()
    memory_name = "MarketTrendsAgentMultiStrategy"
    client = MemoryClient(region_name=region)

    # Find existing memory
    memories = client.list_memories()
    memory_id = None
    for memory in memories:
        if memory["id"].startswith(memory_name):
            memory_id = memory["id"]
            break

    if not memory_id:
        print("No memory found to reset.")
        return

    print(f"Memory: {memory_id}")
    print()
    print("This will clear all conversation data and preferences.")
    print()

    # Confirm
    try:
        response = input("Continue? (yes/no): ").strip().lower()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)

    if response != "yes":
        print("Cancelled.")
        sys.exit(0)

    print()

    # Delete sessions
    if os.path.exists(SESSIONS_FILE):
        print("Deleting sessions... ", end="", flush=True)
        count = delete_all_sessions()
        print(f"done ({count} deleted)")
        if os.path.exists(SESSIONS_FILE):
            os.remove(SESSIONS_FILE)
    else:
        print("No sessions to delete")

    # Delete memory
    print("Deleting memory instance... ", end="", flush=True)
    try:
        client.delete_memory_and_wait(memory_id, max_wait=300, poll_interval=5)
        print("done")
    except Exception as e:
        print(f"failed: {e}")
        sys.exit(1)

    # Wait a bit for propagation
    import time

    print("Waiting for deletion to propagate... ", end="", flush=True)
    time.sleep(5)
    print("done")

    # Recreate memory
    print("Recreating memory... ", end="", flush=True)

    strategies = [
        {
            StrategyType.USER_PREFERENCE.value: {
                "name": "BrokerPreferences",
                "description": "Captures broker preferences, risk tolerance, and investment styles",
                "namespaces": ["market-trends/broker/{actorId}/preferences"],
            }
        },
        {
            StrategyType.SEMANTIC.value: {
                "name": "MarketTrendsSemantic",
                "description": "Stores financial facts, market analysis, and investment insights",
                "namespaces": ["market-trends/broker/{actorId}/semantic"],
            }
        },
    ]

    try:
        memory = client.create_memory_and_wait(
            name=memory_name,
            description="Market Trends Agent with multi-strategy memory",
            strategies=strategies,
            event_expiry_days=90,
            max_wait=300,
            poll_interval=5,
        )
        print("done")
        print()
        print("✓ Reset complete")
    except Exception as e:
        print(f"failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
