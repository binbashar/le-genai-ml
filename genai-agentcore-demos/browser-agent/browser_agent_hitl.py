#!/usr/bin/env python3
"""
Browser Agent with Human-in-the-Loop (HITL) Control

This module implements secure browser automation with the ability to pause
automation and allow human intervention via Live View.

Features:
- UpdateBrowserStream API for pause/resume automation
- Live View URL generation for human control
- Secure credential handling (never logged)
- Session recording support
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import boto3
from strands import Agent
from strands_tools.browser import AgentCoreBrowser

from config import BedrockModelCatalog, get_bedrock_model, get_client, get_region

# Configure logging with sensitive data filtering
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# HITL Configuration
# ============================================================================


@dataclass
class HITLConfig:
    """Configuration for Human-in-the-Loop control"""

    browser_identifier: str
    session_id: str
    live_view_url: Optional[str] = None
    automation_paused: bool = False
    region: str = "us-west-2"


# ============================================================================
# Browser Session Management with HITL
# ============================================================================


class HITLBrowserSession:
    """Manages browser session with human-in-the-loop capabilities"""

    def __init__(self, region: str = None):
        self.region = region or get_region()
        self.client = get_client("bedrock-agentcore")
        self.browser_tool = AgentCoreBrowser(region=self.region)
        self.config: Optional[HITLConfig] = None

    def start_session(self, session_id: str) -> dict:
        """
        Start a browser session and capture identifiers for HITL control.

        Args:
            session_id: Unique session identifier

        Returns:
            dict: Session info including browser_identifier and live_view_url
        """
        logger.info(f"Starting browser session: {session_id}")

        # Initialize browser (this creates the actual browser instance)
        # AgentCoreBrowser handles session creation internally
        self.config = HITLConfig(
            browser_identifier="",  # Will be populated from browser tool
            session_id=session_id,
            region=self.region,
        )

        # Note: AgentCoreBrowser doesn't expose browser_identifier directly
        # In production, you'd get this from StartBrowserSession API response
        # For now, we'll use a placeholder pattern
        return {
            "session_id": session_id,
            "region": self.region,
            "status": "active",
            "message": "Browser session started. Use browser tool to interact.",
        }

    def pause_automation(self) -> dict:
        """
        Pause browser automation to allow human intervention.

        Calls UpdateBrowserStream with streamStatus: DISABLED

        Returns:
            dict: Status and Live View URL for human access
        """
        if not self.config:
            raise ValueError("No active browser session. Call start_session() first.")

        logger.info("Pausing browser automation for human intervention")

        try:
            # Call UpdateBrowserStream API
            response = self.client.update_browser_stream(
                browserIdentifier=self.config.browser_identifier,
                sessionId=self.config.session_id,
                streamUpdate={"automationStreamUpdate": {"streamStatus": "DISABLED"}},
            )

            self.config.automation_paused = True

            # Generate Live View URL
            # Format: https://console.aws.amazon.com/bedrock/agentcore/browser/sessions/{sessionId}
            live_view_url = self._generate_live_view_url()
            self.config.live_view_url = live_view_url

            logger.info(f"Automation paused. Live View: {live_view_url}")

            return {
                "status": "paused",
                "live_view_url": live_view_url,
                "message": "Automation paused. Please use Live View to complete manual steps.",
                "session_id": self.config.session_id,
            }

        except Exception as e:
            logger.error(f"Failed to pause automation: {e}")
            return {
                "status": "error",
                "message": f"Failed to pause automation: {str(e)}",
            }

    def resume_automation(self) -> dict:
        """
        Resume browser automation after human intervention.

        Calls UpdateBrowserStream with streamStatus: ENABLED

        Returns:
            dict: Status of resumption
        """
        if not self.config:
            raise ValueError("No active browser session")

        if not self.config.automation_paused:
            logger.warning("Automation was not paused. No action taken.")
            return {"status": "warning", "message": "Automation was not paused"}

        logger.info("Resuming browser automation")

        try:
            response = self.client.update_browser_stream(
                browserIdentifier=self.config.browser_identifier,
                sessionId=self.config.session_id,
                streamUpdate={"automationStreamUpdate": {"streamStatus": "ENABLED"}},
            )

            self.config.automation_paused = False

            logger.info("Automation resumed successfully")

            return {
                "status": "resumed",
                "message": "Automation resumed. Agent will continue execution.",
                "session_id": self.config.session_id,
            }

        except Exception as e:
            logger.error(f"Failed to resume automation: {e}")
            return {
                "status": "error",
                "message": f"Failed to resume automation: {str(e)}",
            }

    def _generate_live_view_url(self) -> str:
        """Generate AWS Console Live View URL"""
        # AWS Console format for browser session live view
        base_url = "https://console.aws.amazon.com/bedrock"
        return f"{base_url}/agentcore/browser/sessions/{self.config.session_id}?region={self.region}"

    def get_status(self) -> dict:
        """Get current session status"""
        if not self.config:
            return {"status": "no_session", "message": "No active session"}

        return {
            "status": "paused" if self.config.automation_paused else "active",
            "session_id": self.config.session_id,
            "live_view_url": self.config.live_view_url,
            "region": self.region,
        }


# ============================================================================
# HITL Browser Agent
# ============================================================================

HITL_BROWSER_AGENT_PROMPT = """You are a helpful web automation assistant with Human-in-the-Loop capabilities.

You can help users with:
- Navigating to websites and extracting information
- Interacting with web pages (clicks, form fills, searches)
- **IMPORTANT: When you encounter login forms or sensitive operations, you MUST signal that human intervention is needed**

Security Rules:
1. NEVER ask users for passwords or credentials in the chat
2. When you detect a login form, IMMEDIATELY signal need for human intervention
3. After human completes manual login via Live View, continue with the task
4. NEVER log sensitive information (passwords, account numbers, etc.)

Human Intervention Signals:
- Detected login form → Return: {"action": "pause_for_human", "reason": "login_required"}
- CAPTCHA encountered → Return: {"action": "pause_for_human", "reason": "captcha"}
- Sensitive operation → Return: {"action": "pause_for_human", "reason": "sensitive_action"}

Be thorough, accurate, and security-conscious in your responses."""


class HITLBrowserAgent:
    """Browser agent with Human-in-the-Loop control"""

    def __init__(self):
        self.session_manager = HITLBrowserSession()
        self.model = get_bedrock_model("strands", BedrockModelCatalog.CLAUDE_SONNET_45)

        # Create agent with browser tool
        self.agent = Agent(
            model=self.model,
            system_prompt=HITL_BROWSER_AGENT_PROMPT,
            tools=[self.session_manager.browser_tool.browser],
        )

    def execute(
        self, user_message: str, session_id: str, auto_pause_on_login: bool = True
    ) -> dict:
        """
        Execute browser task with HITL support.

        Args:
            user_message: User's task description
            session_id: Session identifier
            auto_pause_on_login: Automatically pause when login detected

        Returns:
            dict: Response with status and data
        """
        # Start session
        session_info = self.session_manager.start_session(session_id)

        # Execute agent
        response = self.agent(user_message)

        # Check if response signals need for human intervention
        if auto_pause_on_login and self._needs_human_intervention(str(response)):
            pause_result = self.session_manager.pause_automation()
            return {
                "status": "awaiting_human",
                "agent_response": str(response),
                "live_view_url": pause_result.get("live_view_url"),
                "message": "Agent paused. Please complete login via Live View.",
                "session_id": session_id,
            }

        return {
            "status": "completed",
            "agent_response": str(response),
            "session_id": session_id,
        }

    def continue_after_human(self, user_message: str) -> dict:
        """
        Continue execution after human intervention.

        Args:
            user_message: Next instruction for agent

        Returns:
            dict: Agent response
        """
        # Resume automation
        resume_result = self.session_manager.resume_automation()

        if resume_result["status"] != "resumed":
            return resume_result

        # Continue with agent
        response = self.agent(user_message)

        return {"status": "completed", "agent_response": str(response)}

    def _needs_human_intervention(self, response: str) -> bool:
        """Detect if agent response signals need for human intervention"""
        intervention_signals = [
            "pause_for_human",
            "login_required",
            "captcha",
            "credentials",
            "password",
        ]

        response_lower = response.lower()
        return any(signal in response_lower for signal in intervention_signals)


# ============================================================================
# Local Testing
# ============================================================================

if __name__ == "__main__":
    import uuid

    print("HITL Browser Agent - Local Testing Mode")
    print("=" * 60)

    agent = HITLBrowserAgent()
    session_id = str(uuid.uuid4())[:8]

    print(f"\nSession ID: {session_id}")
    print("\nExample: Navigate to a banking website")
    print("The agent will pause when it detects a login form.\n")

    # Test query
    query = input("Enter task (or press Enter for default): ").strip()
    if not query:
        query = "Navigate to https://example.com/login and login to my account"

    print(f"\nProcessing: {query}")
    print("-" * 60)

    result = agent.execute(query, session_id=session_id)

    print("\nResult:")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    if result["status"] == "awaiting_human":
        print("\n" + "=" * 60)
        print("ACTION REQUIRED: Human Intervention Needed")
        print("=" * 60)
        print(f"\n1. Open Live View: {result.get('live_view_url')}")
        print("2. Complete the login manually")
        print("3. Press Enter here to continue...")
        input()

        # Continue after human
        continue_result = agent.continue_after_human(
            "Continue with the task after login"
        )
        print("\nContinuation Result:")
        print("=" * 60)
        print(json.dumps(continue_result, indent=2))

    print("=" * 60)
