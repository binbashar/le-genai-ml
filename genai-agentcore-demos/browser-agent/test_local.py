#!/usr/bin/env python3
"""Quick test of browser agent with a predefined query"""

from browser_agent import browser_agent

# Test query
query = "Navigate to https://example.com and tell me what you see"

print("=" * 60)
print(f"Testing Browser Agent")
print("=" * 60)
print(f"\nQuery: {query}\n")
print("-" * 60)

try:
    response = browser_agent(query)
    print("\nAgent Response:")
    print("=" * 60)
    print(response)
    print("=" * 60)
except Exception as e:
    print(f"\nError: {e}")
    import traceback

    traceback.print_exc()
