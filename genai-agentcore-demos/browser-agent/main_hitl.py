#!/usr/bin/env python3
"""
AgentCore Runtime Entrypoint with Human-in-the-Loop (HITL) Support

This module provides the main entrypoint for deploying the HITL browser agent
to AWS Bedrock AgentCore Runtime with support for pause/resume automation.

Features:
- UpdateBrowserStream integration for pause/resume
- Live View URL generation
- Secure credential handling
- Callback mechanism for continuation
"""

import json
import logging
import uuid
from typing import Any, AsyncIterator, Dict

from bedrock_agentcore import BedrockAgentCoreApp

from browser_agent_hitl import HITLBrowserAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# AgentCore Application Setup
# ============================================================================

app = BedrockAgentCoreApp()

# Global agent instance
hitl_agent = HITLBrowserAgent()

# ============================================================================
# Session State Management
# ============================================================================

# In-memory session state (for demo - use DynamoDB in production)
session_states = {}


def get_or_create_session_id(payload: Dict[str, Any]) -> str:
    """Get or create session ID from payload"""
    session_id = payload.get("session_id")

    if not session_id:
        # Generate new session ID
        session_id = str(uuid.uuid4())[:12]
        logger.info(f"Created new session: {session_id}")

    return session_id


def save_session_state(session_id: str, state: Dict[str, Any]):
    """Save session state (in-memory for demo)"""
    session_states[session_id] = state
    logger.info(f"Saved state for session {session_id}: {state.get('status')}")


def get_session_state(session_id: str) -> Dict[str, Any]:
    """Retrieve session state"""
    return session_states.get(session_id, {})


# ============================================================================
# Entrypoint - Streaming Response
# ============================================================================


@app.entrypoint
async def invoke(payload, context) -> AsyncIterator[Dict[str, Any]]:
    """
    Main entrypoint for HITL browser agent with streaming support.

    Payload structure:
        {
            "prompt": str,              # User's task
            "session_id": str,          # Optional session ID
            "action": str,              # Optional: "continue" after human intervention
            "human_completed": bool     # Signal that human finished manual step
        }

    Returns:
        AsyncIterator yielding:
        - {"type": "status", "message": str}
        - {"type": "thinking", "message": str}
        - {"type": "awaiting_human", "live_view_url": str, "message": str}
        - {"type": "final", "result": str}
    """
    user_message = payload.get("prompt", "")
    action = payload.get("action", "start")
    human_completed = payload.get("human_completed", False)

    if not user_message and action != "continue":
        yield {"type": "error", "message": "Missing 'prompt' in payload"}
        return

    # Get or create session
    session_id = get_or_create_session_id(payload)
    session_state = get_session_state(session_id)

    logger.info(
        f"Processing request - Session: {session_id}, Action: {action}, State: {session_state.get('status')}"
    )

    # ========================================================================
    # Case 1: Continue after human intervention
    # ========================================================================

    if action == "continue" or human_completed:
        if session_state.get("status") != "awaiting_human":
            yield {
                "type": "error",
                "message": "Session not in awaiting_human state. Cannot continue.",
            }
            return

        yield {
            "type": "status",
            "message": "Resuming automation after human intervention",
        }

        try:
            # Continue agent execution
            result = hitl_agent.continue_after_human(
                user_message or "Continue with the previous task"
            )

            if result["status"] == "completed":
                # Update session state
                session_state["status"] = "completed"
                save_session_state(session_id, session_state)

                yield {"type": "final", "result": result["agent_response"]}
            else:
                yield {
                    "type": "error",
                    "message": f"Failed to continue: {result.get('message')}",
                }

        except Exception as e:
            logger.error(f"Error continuing after human: {e}")
            yield {"type": "error", "message": f"Error continuing: {str(e)}"}

        return

    # ========================================================================
    # Case 2: Start new task
    # ========================================================================

    yield {
        "type": "status",
        "message": f"Starting browser task (Session: {session_id})",
    }

    try:
        # Execute agent with HITL support
        result = hitl_agent.execute(
            user_message=user_message,
            session_id=session_id,
            auto_pause_on_login=True,  # Auto-pause when login detected
        )

        # Check if human intervention is needed
        if result["status"] == "awaiting_human":
            # Save session state
            session_state = {
                "status": "awaiting_human",
                "live_view_url": result.get("live_view_url"),
                "original_message": user_message,
            }
            save_session_state(session_id, session_state)

            # Yield awaiting_human event
            yield {
                "type": "awaiting_human",
                "session_id": session_id,
                "live_view_url": result.get("live_view_url"),
                "message": result.get("message"),
                "instructions": {
                    "step1": f"Open Live View: {result.get('live_view_url')}",
                    "step2": "Complete the login manually in the browser",
                    "step3": "Send new request with: {'action': 'continue', 'session_id': '<session_id>'}",
                },
            }

            # Also yield the agent's response (what it saw before pausing)
            yield {
                "type": "thinking",
                "message": f"Agent detected login requirement: {result.get('agent_response')}",
            }

        elif result["status"] == "completed":
            # Task completed without human intervention
            session_state = {"status": "completed"}
            save_session_state(session_id, session_state)

            yield {"type": "final", "result": result["agent_response"]}

        else:
            # Error case
            yield {
                "type": "error",
                "message": f"Unexpected status: {result['status']}",
            }

    except Exception as e:
        logger.error(f"Error executing agent: {e}", exc_info=True)
        yield {"type": "error", "message": f"Agent execution failed: {str(e)}"}


# ============================================================================
# HTTP Endpoints (for testing and callbacks)
# ============================================================================


@app.endpoint("/sessions/{session_id}/status", methods=["GET"])
async def get_session_status(session_id: str):
    """Get current session status"""
    state = get_session_state(session_id)

    if not state:
        return {"error": "Session not found"}, 404

    return {
        "session_id": session_id,
        "status": state.get("status"),
        "live_view_url": state.get("live_view_url"),
    }


@app.endpoint("/sessions/{session_id}/continue", methods=["POST"])
async def continue_session(session_id: str, body: dict):
    """
    Signal that human has completed manual intervention.

    Body:
        {
            "next_instruction": str  # Optional next instruction for agent
        }
    """
    state = get_session_state(session_id)

    if not state or state.get("status") != "awaiting_human":
        return {"error": "Session not in awaiting_human state"}, 400

    next_instruction = body.get("next_instruction", "Continue with the task")

    try:
        result = hitl_agent.continue_after_human(next_instruction)

        # Update session state
        state["status"] = "completed"
        save_session_state(session_id, state)

        return {
            "status": "continued",
            "result": result.get("agent_response"),
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Error continuing session: {e}")
        return {"error": str(e)}, 500


# ============================================================================
# Local Development Server
# ============================================================================

if __name__ == "__main__":
    # Start local HTTP server for testing
    # Run with: uv run python main_hitl.py
    #
    # Test with streaming:
    # curl -X POST http://localhost:8080/invocations \
    #      -H "Content-Type: application/json" \
    #      -d '{"prompt": "Navigate to https://example.com/login and login"}'
    #
    # Continue after human:
    # curl -X POST http://localhost:8080/invocations \
    #      -H "Content-Type: application/json" \
    #      -d '{"action": "continue", "session_id": "<session_id>"}'

    print("=" * 60)
    print("HITL Browser Agent - AgentCore Runtime")
    print("=" * 60)
    print("\nStarting local server on http://localhost:8080")
    print("\nEndpoints:")
    print("  POST   /invocations")
    print("  GET    /sessions/{session_id}/status")
    print("  POST   /sessions/{session_id}/continue")
    print("\n" + "=" * 60)

    app.run()
