import json
import logging
import re
import sys
import time
import uuid
from pathlib import Path

import boto3
import requests
import streamlit as st
import yaml

from shared.auth_utils import authenticate, invoke_with_token, load_auth_config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION CONFIGURATION
# ============================================================================
# Authentication is detected DYNAMICALLY per agent:
# - Each agent has its own .auth_config file
# - This UI adapts to mixed scenarios (e.g., finance uses Cognito, market uses IAM)
#
# ============================================================================


# Load configuration files
@st.cache_resource
def load_config():
    """Load agent and use case configurations"""
    config_dir = Path(__file__).parent / "config"

    with open(config_dir / "agents.yaml", "r") as f:
        agents_config = yaml.safe_load(f)

    with open(config_dir / "use_cases.yaml", "r") as f:
        use_cases_config = yaml.safe_load(f)

    return agents_config, use_cases_config


# Load configs
agents_config, use_cases_config = load_config()

# Extract settings
AWS_REGION = agents_config["aws"]["region"]
TIMEOUT_SECONDS = agents_config["aws"]["timeout_seconds"]


# Load auth config for each agent dynamically
@st.cache_resource
def load_agents_auth_config():
    """Load authentication configuration for each agent"""
    return {
        "finance_assistant": load_auth_config(
            Path("../finance-personal-assistant/.auth_config")
        ),
        "market_trends": load_auth_config(Path("../market-trends-agent/.auth_config")),
    }


AGENTS_AUTH = load_agents_auth_config()


def should_use_auth() -> tuple[bool, str]:
    """Check if any agent requires authentication"""
    auth_agents = [name for name, config in AGENTS_AUTH.items() if config is not None]

    if auth_agents:
        return True, f"Authentication enabled for: {', '.join(auth_agents)}"
    return False, "No authentication configured"


def get_agent_auth_config(agent_type: str) -> dict:
    """Get authentication configuration for specific agent"""
    return AGENTS_AUTH.get(agent_type)


# Page configuration
st.set_page_config(
    page_title="AWS AgentCore FinTech Demo", page_icon="🏦", layout="centered"
)

# Sidebar with configuration
with st.sidebar:
    st.markdown("### AWS Connection")

    # AWS connectivity verification
    try:
        sts = boto3.client("sts", region_name=AWS_REGION)
        identity = sts.get_caller_identity()
        st.success("✅ Connected")
    except Exception:
        st.error("❌ Not Connected")
        st.caption("Set AWS_PROFILE environment variable or configure credentials")
        st.stop()

    st.markdown("---")

    # Authentication (if any agent requires it)
    use_auth, reason = should_use_auth()

    if use_auth:
        st.markdown("### 🔐 Authentication")
        logger.info(f"Authentication enabled: {reason}")

        # Check if user is logged in
        if "auth_token" not in st.session_state:
            # Login form
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="broker_demo")
                password = st.text_input(
                    "Password", type="password", placeholder="DemoPass123!"
                )
                agent_for_login = st.radio(
                    "Agent to access:",
                    ["finance_assistant", "market_trends"],
                    format_func=lambda x: agents_config["agents"][x]["name"],
                )
                submit = st.form_submit_button("Login", use_container_width=True)

                if submit:
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        # Check if selected agent has authentication configured
                        auth_config = get_agent_auth_config(agent_for_login)

                        if not auth_config:
                            st.error(
                                f"❌ Agent '{agent_for_login}' does not have authentication configured"
                            )
                            st.caption(
                                f"Run `uv run setup_identity.py --agent {agent_for_login}` to configure authentication"
                            )
                        else:
                            try:
                                # Authenticate using generic auth_utils
                                with st.spinner("Authenticating..."):
                                    auth_result = authenticate(
                                        auth_config, username, password
                                    )

                                # Store auth token and user info in session
                                st.session_state["auth_token"] = auth_result[
                                    "AccessToken"
                                ]
                                st.session_state["username"] = username
                                st.session_state["agent_type"] = agent_for_login
                                st.success(f"Welcome, {username}!")
                                st.rerun()

                            except ValueError as e:
                                st.error(str(e))
                            except Exception as e:
                                st.error(f"Authentication failed: {e}")
                                logger.error(f"Login error: {e}")

            st.stop()  # Don't show agent selector until logged in

        else:
            # User is logged in - show info and logout
            st.success(f"✓ Logged in as: {st.session_state.get('username', 'User')}")

            if st.button("Logout", use_container_width=True):
                # Clear session state
                for key in ["auth_token", "username", "agent_type"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

            # Use the agent type from login
            agent_type = st.session_state.get("agent_type", "finance_assistant")

        st.markdown("---")

    else:
        # No authentication - show regular agent selector
        st.markdown("### Agent Selection")

        agent_type = st.radio(
            "Select Agent:",
            ["finance_assistant", "market_trends"],
            format_func=lambda x: agents_config["agents"][x]["name"],
            label_visibility="collapsed",
        )

    st.caption("🏦 AWS GenAI Loft FinTech Event")
    st.caption("Built with Amazon Bedrock AgentCore")

# Title
st.title("🏦 AWS AgentCore FinTech Demo")

# Get agent config and use cases
agent_info = agents_config["agents"][agent_type]
use_cases = use_cases_config[agent_type]

# Use case selector
selected_use_case = st.selectbox(
    "Choose a scenario:", options=use_cases, format_func=lambda x: x["title"]
)

# Display use case details (no expander)
st.markdown(f"**Persona:** {selected_use_case['persona']}")
st.markdown(f"**Description:** {selected_use_case['description']}")
st.markdown("")

# Editable prompt
custom_prompt = st.text_area(
    "Your message:",
    value=selected_use_case["prompt"],
    height=120,
    placeholder="Type your message here...",
    help="Modify this prompt to experiment with different queries",
)


def escape_latex_chars(text):
    """
    Escape characters that trigger LaTeX rendering in Streamlit.
    Prevents "$1,200 per month" from being interpreted as LaTeX math mode.
    """
    # Escape dollar signs to prevent LaTeX interpretation
    text = re.sub(r"\$", r"\\$", text)

    return text


# Generator function for st.write_stream()
def stream_agent_response(response_stream, tool_placeholder, timeout_seconds):
    """
    Generator that yields tokens from AgentCore stream.
    Handles tool messages as side effects.
    Ensures markdown headers start on their own line.
    """
    start_time = time.time()
    prev_char = ""  # Track last character from previous token for header formatting

    for line in response_stream.iter_lines(chunk_size=10):
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logger.warning(f"Response timeout after {timeout_seconds} seconds")
            break

        if not line:
            continue

        # Decode line
        line_str = line.decode("utf-8") if isinstance(line, bytes) else line

        # Parse Server-Sent Events format (SSE)
        if line_str.startswith("data: "):
            data_str = line_str[6:]  # Remove "data: " prefix

            try:
                event = json.loads(data_str)

                # Log ALL event types for debugging
                if isinstance(event, dict):
                    event_type = event.get("type", "unknown")
                    logger.debug(f"EVENT: type={event_type}, keys={list(event.keys())}")

                # Handle tool messages (side effect - updates UI)
                if isinstance(event, dict) and event.get("type") == "thinking":
                    tool_msg = event.get("message", "")
                    if tool_msg:
                        tool_placeholder.caption(f"🔧 {tool_msg}")
                        logger.info(f"Tool: {tool_msg}")

                # Yield response tokens (with escaping and header formatting)
                elif isinstance(event, str):
                    token = escape_latex_chars(event)

                    # Fix markdown headers: if token starts with # and previous char wasn't newline
                    if (
                        token
                        and re.match(r"^#{1,6}\s", token)
                        and prev_char
                        and prev_char != "\n"
                    ):
                        token = "\n" + token

                    if token:
                        prev_char = token[-1]
                        yield token

                elif isinstance(event, dict) and event.get("type") == "stream_token":
                    token = event.get("token", "")
                    if token:
                        token = escape_latex_chars(token)

                        # Fix markdown headers: if token starts with # and previous char wasn't newline
                        if (
                            re.match(r"^#{1,6}\s", token)
                            and prev_char
                            and prev_char != "\n"
                        ):
                            token = "\n" + token

                        prev_char = token[-1]
                        yield token

                elif isinstance(event, dict) and event.get("type") == "final":
                    result = event.get("result", "")
                    logger.info(
                        f"FINAL EVENT: result length={len(result)}, contains #={('#' in result)}"
                    )
                    if result:
                        yield result

            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {e}")
                continue


# Run agent button
if st.button("🚀 Run Agent", type="primary", use_container_width=True):
    if not custom_prompt.strip():
        st.warning("Please enter a prompt")
        st.stop()

    # Create placeholders
    st.markdown("---")
    tool_placeholder = st.empty()  # For tool execution messages
    temp_placeholder = st.empty()  # Temporary for streaming (will be replaced)

    try:
        logger.info(f"Starting agent invocation for agent_type: {agent_type}")

        # Brief spinner only for API connection
        with st.spinner("Connecting to agent..."):
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            logger.info(f"Generated session ID: {session_id}")

            # Check if agent has authentication configured
            agent_auth_config = get_agent_auth_config(agent_type)

            if agent_auth_config:
                # Agent requires authentication - use HTTP with JWT
                logger.info(
                    f"Using {agent_auth_config.get('provider', 'unknown')} authentication with HTTP invocation"
                )

                auth_token = st.session_state.get("auth_token")
                if not auth_token:
                    st.error("Not authenticated. Please refresh the page to login.")
                    st.stop()

                try:
                    response = invoke_with_token(
                        agent_arn=agent_info["arn"],
                        token=auth_token,
                        prompt=custom_prompt,
                        session_id=session_id,
                        region=AWS_REGION,
                        timeout=TIMEOUT_SECONDS,
                    )
                    logger.info(
                        "Agent invocation successful (authenticated), processing event stream"
                    )

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 401:
                        st.error("Authentication token expired. Please login again.")
                        # Clear session and force re-login
                        for key in ["auth_token", "username", "agent_type"]:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.stop()
                    else:
                        raise

            else:
                # No authentication - use IAM with boto3
                logger.info("Using IAM authentication with boto3")

                client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
                logger.info(
                    f"Created bedrock-agentcore client for region: {AWS_REGION}"
                )

                response = client.invoke_agent_runtime(
                    agentRuntimeArn=agent_info["arn"],
                    payload=json.dumps(
                        {"prompt": custom_prompt, "session_id": session_id}
                    ),
                )

                logger.info(
                    "Agent invocation successful (IAM), processing event stream"
                )

        # Stream response to temporary placeholder
        # For authenticated/HTTP: response is already the stream
        # For IAM/boto3: response["response"] is the stream
        response_stream = response if agent_auth_config else response["response"]

        with temp_placeholder.container():
            response_text = st.write_stream(
                stream_agent_response(
                    response_stream, tool_placeholder, TIMEOUT_SECONDS
                )
            )

        # Clear temporary placeholder
        temp_placeholder.empty()

        # Post-process: Extract thinking content and display
        if response_text and response_text.strip():
            # Extract thinking content using regex
            thinking_pattern = r"<thinking>(.*?)</thinking>"
            thinking_matches = re.findall(thinking_pattern, response_text, re.DOTALL)

            # Display thinking in expander if found
            if thinking_matches:
                thinking_content = "\n\n".join(thinking_matches)
                with st.expander("💭 Thinking Process", expanded=False):
                    st.text(thinking_content.strip())

            # Remove thinking tags from main response
            cleaned_response = re.sub(
                thinking_pattern, "", response_text, flags=re.DOTALL
            ).strip()

            # Display cleaned response
            if cleaned_response:
                st.markdown(cleaned_response)
                logger.info(
                    f"Response complete ({len(cleaned_response)} chars, thinking: {len(thinking_content) if thinking_matches else 0} chars)"
                )
            else:
                st.info("No response received")
                logger.warning("No response text after removing thinking tags")
        else:
            st.info("No response received")
            logger.warning("No response text received from agent")

    except Exception as e:
        logger.error(f"Error during agent invocation: {str(e)}", exc_info=True)
        st.error(f"Error: {str(e)}")
        st.caption("Please check your AWS credentials and agent configuration.")
