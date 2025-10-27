import json
import logging
import re
import time
import uuid
from pathlib import Path

import boto3
import requests
import streamlit as st
import yaml
from shared.auth_utils import authenticate, invoke_with_token

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION CONFIGURATION (Per-Agent)
# ============================================================================
# Each agent in agents.yaml has oauth_config:
# - oauth_config: null → Uses AWS IAM credentials (no login required)
# - oauth_config: {...} → Requires OAuth2/JWT login
#
# OAuth config synced from SSM by sync.py (runs before Streamlit starts)
#
# UX Flow:
# 1. User selects agent (🔐 = OAuth, 🔑 = IAM)
# 2. OAuth agent → show login form
# 3. IAM agent → proceed directly
# ============================================================================


# Load configuration files
@st.cache_resource
def load_config():
    """Load agent configurations"""
    config_dir = Path(__file__).parent / "config"

    with open(config_dir / "agents.yaml", "r") as f:
        agents_config = yaml.safe_load(f)

    return agents_config


# Load configs
agents_config = load_config()

# Extract settings
AWS_REGION = agents_config["aws"]["region"]
TIMEOUT_SECONDS = agents_config["aws"]["timeout_seconds"]


def get_agent_auth_config(agent_type: str) -> dict | None:
    """Get OAuth configuration for specific agent (returns None if agent uses IAM)"""
    return agents_config["agents"][agent_type].get("oauth_config")


def get_or_create_session_id(agent_type: str) -> str:
    """Get session ID from file or create new one"""
    sessions_dir = Path(__file__).parent / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    session_file = sessions_dir / f".{agent_type}"

    # Try to read existing session ID
    if session_file.exists():
        try:
            session_id = session_file.read_text().strip()
            if session_id and len(session_id) >= 33:  # AWS minimum
                logger.info(f"Loaded session ID for {agent_type}: {session_id}")
                return session_id
        except Exception as e:
            logger.warning(f"Failed to read session file: {e}")

    # Generate new session ID
    session_id = str(uuid.uuid4())

    # Save to file
    try:
        session_file.write_text(session_id)
        logger.info(f"Created new session ID for {agent_type}: {session_id}")
    except Exception as e:
        logger.error(f"Failed to save session file: {e}")

    return session_id


# Page configuration
st.set_page_config(
    page_title="AWS AgentCore FinTech Demo", page_icon="🏦", layout="centered"
)

# Sidebar with configuration
with st.sidebar:
    # AWS connectivity verification
    try:
        sts = boto3.client("sts", region_name=AWS_REGION)
        identity = sts.get_caller_identity()
        st.success("✅ AWS Connected")
    except Exception:
        st.error("❌ AWS Not Connected")
        st.caption("Set AWS_PROFILE or configure credentials")
        st.stop()

    st.markdown("---")

    # Agent Selection
    all_agents = list(agents_config["agents"].keys())

    # Agent selector with auth mode indicator
    def format_agent_name(agent_key: str) -> str:
        agent_info = agents_config["agents"][agent_key]
        icon = "🔐" if agent_info.get("oauth_config") else "🔑"
        return f"{icon} {agent_info['name']}"

    selected_agent = st.radio(
        "Select Agent",
        all_agents,
        format_func=format_agent_name,
        key="agent_selector",
    )

    # Get selected agent config
    selected_agent_info = agents_config["agents"][selected_agent]
    agent_type = selected_agent

    # Show authentication status (minimal)
    if selected_agent_info.get("oauth_config"):
        current_agent_in_session = st.session_state.get("agent_type")

        if current_agent_in_session == selected_agent:
            # User is logged in - show logout button
            st.markdown("")  # Spacer
            st.caption(f"Logged in as **{st.session_state.get('username', 'User')}**")
            if st.button("Logout", use_container_width=True):
                # Clear session state
                for key in ["auth_token", "username", "agent_type"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    st.markdown("---")

    # Footer
    st.caption("🏦 AWS GenAI Loft FinTech Event")
    st.caption("Built with Amazon Bedrock AgentCore")

# ============================================================================
# MAIN SCREEN: Authentication Gate (for OAuth agents)
# ============================================================================
# Check if selected agent requires OAuth and user is not logged in
agent_info = agents_config["agents"][agent_type]
current_agent_in_session = st.session_state.get("agent_type")

if agent_info.get("oauth_config") and current_agent_in_session != agent_type:
    # Show login form in main screen (left-aligned)
    # Single clean title with agent name
    st.title(agent_info['name'])
    st.markdown("")

    # Left-aligned login form (max width to match title)
    with st.form("login_form", clear_on_submit=False):
        st.markdown("Please enter your credentials to continue:")
        st.markdown("")

        username = st.text_input("Username", placeholder="broker_demo", key="username_input")
        password = st.text_input("Password", type="password", placeholder="DemoPass123!", key="password_input")

        st.markdown("")
        submit = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submit:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                # Get OAuth config for selected agent
                auth_config = get_agent_auth_config(agent_type)

                if auth_config:
                    try:
                        # Authenticate using generic auth_utils
                        with st.spinner("Authenticating..."):
                            auth_result = authenticate(auth_config, username, password)

                        # Store auth token and user info in session
                        st.session_state["auth_token"] = auth_result["AccessToken"]
                        st.session_state["username"] = username
                        st.session_state["agent_type"] = agent_type
                        st.success(f"✅ Welcome, {username}!")
                        time.sleep(0.5)  # Brief pause to show success
                        st.rerun()

                    except ValueError as e:
                        st.error(f"❌ {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Authentication failed: {e}")
                        logger.error(f"Login error: {e}")

    st.stop()  # Don't render the rest of the app until logged in

# ============================================================================
# MAIN SCREEN: Chat Interface (authenticated or IAM)
# ============================================================================

# Get agent config
agent_info = agents_config["agents"][agent_type]

# Title with agent name
st.title(agent_info['name'])

# Initialize session state for this agent
# Each agent gets its own message history and session ID
messages_key = f"messages_{agent_type}"
session_id_key = f"session_id_{agent_type}"

if messages_key not in st.session_state:
    st.session_state[messages_key] = []

if session_id_key not in st.session_state:
    st.session_state[session_id_key] = get_or_create_session_id(agent_type)

# Display chat messages from history
for message in st.session_state[messages_key]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


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


# React to user input
if prompt := st.chat_input("Type your message here..."):
    # Get session ID for this agent
    session_id = st.session_state[session_id_key]

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add user message to chat history
    st.session_state[messages_key].append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        tool_placeholder = st.empty()  # For tool execution messages

        try:
            logger.info(f"Starting agent invocation for agent_type: {agent_type}")

            # Brief spinner only for API connection
            with st.spinner("Connecting to agent..."):
                logger.info(f"Using session ID: {session_id}")

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
                            prompt=prompt,
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
                            {"prompt": prompt, "session_id": session_id}
                        ),
                    )

                    logger.info(
                        "Agent invocation successful (IAM), processing event stream"
                    )

            # Stream response
            # For authenticated/HTTP: response is already the stream
            # For IAM/boto3: response["response"] is the stream
            response_stream = response if agent_auth_config else response["response"]

            response_text = st.write_stream(
                stream_agent_response(
                    response_stream, tool_placeholder, TIMEOUT_SECONDS
                )
            )

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

                # Add assistant response to chat history
                if cleaned_response:
                    st.session_state[messages_key].append({"role": "assistant", "content": cleaned_response})
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
            error_message = f"Error: {str(e)}"
            st.error(error_message)
            st.caption("Please check your AWS credentials and agent configuration.")
            # Add error to chat history
            st.session_state[messages_key].append({"role": "assistant", "content": error_message})
