#!/usr/bin/env python3
"""AgentCore Runtime entrypoint for Browser Agent"""

from bedrock_agentcore import BedrockAgentCoreApp

from browser_agent import browser_agent

# ============================================================================
# AgentCore Application Setup
# ============================================================================

app = BedrockAgentCoreApp()

# ============================================================================
# Entrypoint
# ============================================================================


@app.entrypoint
def invoke(payload, context):
    """
    Main entrypoint for AgentCore Runtime.

    Args:
        payload: Request payload containing:
            - prompt (str): User's web automation task
        context: AgentCore Runtime context

    Returns:
        dict: Response containing:
            - result (str): Agent's response

    Example payload:
        {
            "prompt": "Navigate to https://example.com and tell me what you see"
        }
    """
    user_message = payload.get("prompt", "")

    if not user_message:
        return {"error": "Missing 'prompt' in payload"}

    # Invoke browser agent
    response = browser_agent(user_message)

    return {"result": str(response)}


# ============================================================================
# Local Development Server
# ============================================================================

if __name__ == "__main__":
    # Start local HTTP server for testing
    # Run with: uv run python main.py
    # Test with: curl -X POST http://localhost:8080/invocations \
    #            -H "Content-Type: application/json" \
    #            -d '{"prompt": "Navigate to https://example.com"}'
    app.run()
