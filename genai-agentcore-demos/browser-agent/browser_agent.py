#!/usr/bin/env python3
"""Browser Agent with AgentCoreBrowser for web automation tasks"""

from strands import Agent
from strands_tools.browser import AgentCoreBrowser

from config import BedrockModelCatalog, get_bedrock_model, get_region

# ============================================================================
# Browser Agent System Prompt
# ============================================================================

BROWSER_AGENT_PROMPT = """You are a helpful web automation assistant powered by Amazon Bedrock AgentCore Browser.

You can help users with:
- Navigating to websites and extracting information
- Searching for content across web pages
- Reading and summarizing web articles
- Filling out forms and interacting with page elements
- Clicking buttons and links
- Taking screenshots of pages

When given a task:
1. Break it down into clear steps
2. Use the browser tool to execute each step
3. Provide clear feedback about what you're doing
4. Extract and present relevant information to the user

Be thorough, accurate, and helpful in your responses."""

# ============================================================================
# Initialize Browser Tool and Agent
# ============================================================================

# Initialize browser tool (AWS-managed browser environment)
browser_tool = AgentCoreBrowser(region=get_region())

# Create agent with Claude Sonnet 4.5 (reliable for complex browser tasks)
model = get_bedrock_model("strands", BedrockModelCatalog.CLAUDE_SONNET_45)

browser_agent = Agent(
    model=model,
    system_prompt=BROWSER_AGENT_PROMPT,
    tools=[browser_tool.browser],
)

# ============================================================================
# Local Testing
# ============================================================================

if __name__ == "__main__":
    print("Browser Agent - Local Testing Mode")
    print("=" * 60)
    print("\nExample queries:")
    print("- Navigate to https://example.com and tell me what you see")
    print("- Search for 'AWS Bedrock' on Google and summarize the results")
    print("- Go to https://docs.aws.amazon.com and find information about AgentCore")
    print("\n" + "=" * 60)

    query = input("\nEnter your query (or press Enter for default): ").strip()

    if not query:
        query = "Navigate to https://example.com and tell me what you see"
        print(f"\nUsing default query: {query}")

    print(f"\nProcessing: {query}")
    print("-" * 60)

    response = browser_agent(query)

    print("\nAgent Response:")
    print("=" * 60)
    print(response)
    print("=" * 60)
