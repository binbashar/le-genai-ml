#!/usr/bin/env python3
"""
Interactive CLI chat with Market Trends Agent
Session-based conversation management for demo/academic use
"""

import argparse
import json
import logging
import sys
import termios

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config import get_client
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from session_manager import (
    create_session,
    list_sessions,
    update_session_timestamp,
)

console = Console()
logger = logging.getLogger(__name__)


class MarkdownStreamRenderer:
    """Handles incremental markdown rendering with Rich Live display"""

    def __init__(self):
        self.items = []  # List of (type, content) tuples to maintain chronological order
        self.current_response_buffer = ""  # Buffer for accumulating response tokens
        self.live = None

    def start(self):
        """Start the live display"""
        self.live = Live(console=console, auto_refresh=False)
        self.live.start()

    def stop(self):
        """Stop the live display"""
        if self.live:
            self.live.stop()
            self.live = None

    def add_thinking(self, message: str):
        """Add a thinking message inline to the conversation"""
        # Flush current response buffer before adding thinking message
        if self.current_response_buffer:
            self.items.append(("response", self.current_response_buffer))
            self.current_response_buffer = ""

        # Add thinking message to timeline
        self.items.append(("thinking", message))
        self._update_display()

    def add_token(self, token: str):
        """Add a token to the accumulated text"""
        self.current_response_buffer += token
        self._update_display()

    def _update_display(self):
        """Update the live display with current content"""
        if not self.live:
            return

        # Build composite view in chronological order
        renderables = []

        # Always add "Agent:" label at the beginning if we have content
        if self.items or self.current_response_buffer:
            renderables.append(Text("Agent:", style="bold magenta"))
            renderables.append(Text())  # Empty line after label

        prev_type = None

        for item_type, content in self.items:
            # Add spacing between thinking messages and response content
            if prev_type == "thinking" and item_type == "response":
                renderables.append(Text())  # Empty line for spacing

            if item_type == "thinking":
                # Render thinking message with dim style
                renderables.append(Text(content, style="dim white"))
            elif item_type == "response":
                # Render response content as markdown
                try:
                    renderables.append(Markdown(content))
                except Exception:
                    renderables.append(Text(content))

            prev_type = item_type

        # Add current response buffer (in progress)
        if self.current_response_buffer:
            # Add spacing if previous item was a thinking message
            if prev_type == "thinking":
                renderables.append(Text())  # Empty line for spacing

            try:
                renderables.append(Markdown(self.current_response_buffer))
            except Exception:
                renderables.append(Text(self.current_response_buffer))

        # Update live display with composite view
        if renderables:
            self.live.update(Group(*renderables), refresh=True)


class StreamingResponseHandler:
    """Handles streaming event-stream responses from AgentCore Runtime"""

    def __init__(self, debug=False):
        self.renderer = MarkdownStreamRenderer()
        self.debug = debug

    def handle_stream(self, response):
        """
        Process streaming response from AgentCore Runtime

        Args:
            response: boto3 response object with event-stream
        """
        self.renderer.start()

        try:
            # Process event stream line by line
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")

                    # Parse Server-Sent Events format
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type")

                            # Debug logging
                            if self.debug:
                                logger.debug(f"Event type: {event_type}")
                                if event_type == "thinking":
                                    logger.debug(
                                        f"Tool message: {event.get('message')}"
                                    )
                                elif event_type == "error":
                                    logger.debug(f"Error event: {event}")
                                    logger.debug(
                                        f"Full error details: {json.dumps(event, indent=2)}"
                                    )

                            if event_type == "thinking":
                                # Show tool execution progress
                                message = event.get("message", "")
                                self.renderer.add_thinking(message)

                            elif event_type == "stream_token":
                                # Add token to accumulated response
                                token = event.get("token", "")
                                if token:
                                    self.renderer.add_token(token)

                            elif event_type == "final":
                                # Final response received
                                result = event.get("result", "")
                                # Make sure we have the complete response
                                if result and not self.renderer.current_response_buffer:
                                    self.renderer.current_response_buffer = result
                                    self.renderer._update_display()

                            elif event_type == "error":
                                # Handle error
                                error_msg = event.get("message", "Unknown error")
                                console.print(f"\n[red]Error: {error_msg}[/red]")
                                if self.debug:
                                    console.print(
                                        "[yellow]Debug - Full error event:[/yellow]"
                                    )
                                    console.print(
                                        f"[dim]{json.dumps(event, indent=2)}[/dim]"
                                    )

                        except json.JSONDecodeError as e:
                            # If not JSON, print raw line
                            if self.debug:
                                logger.debug(f"JSON decode error: {e}")
                                logger.debug(f"Raw data: {data_str}")
                            console.print(f"[dim]{data_str}[/dim]")

        finally:
            self.renderer.stop()
            # Add spacing after response before next prompt
            print("\n")


def verify_aws_credentials() -> bool:
    """
    Verify AWS credentials are configured and valid.
    Returns True if credentials are valid, False otherwise.
    """
    try:
        # Try to get caller identity to verify credentials
        sts = boto3.client("sts")
        sts.get_caller_identity()
        return True
    except NoCredentialsError:
        print()
        print("AWS credentials not found.")
        print()
        print("Configure credentials with: aws configure sso")
        print(
            "Or see: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html"
        )
        print()
        return False
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        print()
        print(f"AWS authentication failed: {error_code}")
        print()
        print("Please verify your credentials and try again.")
        print()
        return False
    except Exception as e:
        print()
        print(f"Failed to verify AWS credentials: {str(e)}")
        print()
        return False


def invoke_agent(runtime_arn: str, prompt: str, session_id: str, debug: bool = False):
    """
    Invoke the deployed agent with session context.
    Handles both streaming and non-streaming responses.

    Args:
        runtime_arn: AgentCore Runtime ARN
        prompt: User input message
        session_id: Session identifier
        debug: Enable debug logging

    Returns:
        For streaming: None (displays directly)
        For non-streaming: str response
    """
    try:
        if debug:
            logger.debug(f"Invoking agent with prompt: {prompt}")
            logger.debug(f"Session ID: {session_id}")

        client = get_client("bedrock-agentcore")
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=json.dumps({"prompt": prompt, "session_id": session_id}),
        )

        # Check if response is streaming
        content_type = response.get("contentType", "")

        if debug:
            logger.debug(f"Response content type: {content_type}")

        if "text/event-stream" in content_type:
            # Handle streaming response with our handler
            handler = StreamingResponseHandler(debug=debug)
            handler.handle_stream(response)
            return None  # Response already displayed

        else:
            # Handle regular JSON response (backwards compatibility)
            if "response" in response:
                raw_response = response["response"].read().decode("utf-8")
                if debug:
                    logger.debug(f"Raw response: {raw_response}")

                try:
                    parsed = json.loads(raw_response)
                    if isinstance(parsed, dict):
                        return parsed.get("result", raw_response)
                    return raw_response
                except json.JSONDecodeError:
                    return raw_response
            return str(response)

    except Exception as e:
        if debug:
            logger.exception("Exception during agent invocation")
        return f"Error: {e}"


def print_help():
    """Show example queries"""
    print("\nExample queries:")
    print("  - Hi, I'm [Name] from [Company]. I focus on [investment style]")
    print("  - What do you remember about my preferences?")
    print("  - Get me Apple's current stock price")
    print("  - Find recent Bloomberg news about AI stocks")
    print("\nCommands:")
    print("  - /sessions - Manage sessions")
    print("  - help      - Show this help")
    print("  - quit      - Exit chat")


def show_session_menu() -> str:
    """Display session selection menu and return chosen session ID"""
    sessions = list_sessions()

    print("─" * 50)
    print("Select a session to start:")
    print()

    if not sessions:
        print("No sessions found. Creating new session.")
        session = create_session()
        short_id = session["id"][:6]
        print(f"Session: {short_id}")
        print()
        return session["id"]

    print("  1. New session")

    for idx, session in enumerate(sessions, start=2):
        print(f"  {idx}. [{session['short_id']}] {session['display_time']}")

    print()

    while True:
        try:
            choice = input(f"Choice (1-{len(sessions) + 1}): ").strip()

            if not choice:
                continue

            choice_num = int(choice)

            if choice_num == 1:
                # Create new session
                session = create_session()
                short_id = session["id"][:6]
                print("=" * 50)
                print(f"\nCreating session {short_id}...")
                return session["id"]

            elif 2 <= choice_num <= len(sessions) + 1:
                # Select existing session
                selected = sessions[choice_num - 2]
                print(f"\nLoading session {selected['short_id']}...")
                return selected["id"]

            else:
                print(f"Invalid choice. Enter 1-{len(sessions) + 1}")

        except ValueError:
            print("Invalid input. Enter a number.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Interactive CLI chat with Market Trends Agent"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to see detailed tool execution and error information",
    )
    args = parser.parse_args()

    # Configure logging
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info("Debug logging enabled")
    else:
        logging.basicConfig(level=logging.WARNING)

    # Verify AWS credentials first
    if not verify_aws_credentials():
        sys.exit(1)

    # Load agent ARN
    try:
        with open(".agent_arn", "r") as f:
            runtime_arn = f.read().strip()
    except FileNotFoundError:
        print()
        print("Agent Not Deployed")
        print("─" * 50)
        print()
        print("No .agent_arn file found. Please deploy the agent first:")
        print()
        print("  uv run python deploy.py")
        print()
        sys.exit(1)

    # Chat header
    print()
    print("Market Trends Agent")
    if args.debug:
        print("🐛 DEBUG MODE ENABLED")
    print("─" * 50)
    print()
    print("Type '/sessions' to manage sessions, 'help' for examples, 'quit' to exit")
    print()

    # Session created lazily after first query
    session_id = None

    # Main chat loop
    try:
        while True:
            try:
                # Get user input with styled prompt
                console.print(Text("You:", style="bold magenta"), end=" ")
                user_input = input().strip()

                # Flush stdin buffer to prevent queued lines from being processed (only if stdin is a tty)
                if sys.stdin.isatty():
                    termios.tcflush(sys.stdin, termios.TCIFLUSH)

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ["quit", "exit", "bye"]:
                    break

                if user_input.lower() == "help":
                    print_help()
                    continue

                if user_input.lower() == "/sessions":
                    session_id = show_session_menu()
                    print()
                    continue

                # Create session on first query
                if session_id is None:
                    session = create_session()
                    session_id = session["id"]

                # Call agent with debug flag
                response = invoke_agent(
                    runtime_arn, user_input, session_id, debug=args.debug
                )

                # Only render if we got a non-streaming response
                # (streaming responses are already displayed)
                if response is not None:
                    print()
                    console.print(Text("Agent:", style="bold magenta"))
                    print()
                    console.print(Markdown(response))
                    print("\n")

            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")
                if args.debug:
                    logger.exception("Exception in main chat loop")
                print()

    except KeyboardInterrupt:
        print("\n")

    finally:
        # Update session timestamp on exit if session was created
        if session_id:
            update_session_timestamp(session_id)
            print("Session saved.")


if __name__ == "__main__":
    main()
