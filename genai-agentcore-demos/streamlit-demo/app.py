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
from shared.auth_utils import (
    authenticate,
    extract_oauth_config_from_ssm,
    invoke_with_token,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION CONFIGURATION (Per-Agent, AWS Best Practice)
# ============================================================================
# Each agent in agents.yaml has its own auth_mode:
# - auth_mode: "oauth" → Requires user login with OAuth2/JWT (reads from SSM)
# - auth_mode: "iam"   → Uses AWS IAM credentials (default, no login)
#
# OAuth config is read from SSM: /agentcore/{agent_name}/oauth-config
# This allows Streamlit to be deployed independently without file dependencies
#
# UX Flow (Agent-First Design):
# 1. User selects agent from selector (🔐 = OAuth, 🔑 = IAM)
# 2. If OAuth agent → show login form for that specific agent
# 3. If IAM agent → proceed directly (implicit authentication)
# 4. Switching agents → re-authenticate if needed (independent auth per agent)
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


# Load OAuth config for agents with auth_mode="oauth"
@st.cache_resource
def load_agents_auth_config():
    """Load OAuth2 configuration from SSM for agents with auth_mode='oauth' (AWS best practice)"""
    auth_configs = {}

    for agent_key, agent_info in agents_config["agents"].items():
        auth_mode = agent_info.get(
            "auth_mode", "iam"
        )  # Default to IAM if not specified

        if auth_mode == "oauth":
            agent_name = agent_info.get("agent_name")
            if agent_name:
                # Read OAuth config from SSM: /agentcore/{agent_name}/oauth-config
                oauth_config = extract_oauth_config_from_ssm(
                    agent_name=agent_name, region=AWS_REGION
                )
                if oauth_config:
                    auth_configs[agent_key] = oauth_config
                    logger.info(
                        f"Loaded OAuth config for {agent_key} from SSM (/agentcore/{agent_name}/oauth-config)"
                    )
                else:
                    logger.warning(
                        f"Agent {agent_key} has auth_mode='oauth' but no OAuth config found in SSM"
                    )
            else:
                logger.warning(
                    f"Agent {agent_key} has auth_mode='oauth' but no agent_name specified"
                )
        else:
            logger.debug(
                f"Agent {agent_key} using IAM authentication (auth_mode='{auth_mode}')"
            )

    return auth_configs


AGENTS_AUTH = load_agents_auth_config()


def get_agent_auth_config(agent_type: str) -> dict | None:
    """Get OAuth configuration for specific agent (returns None if agent uses IAM)"""
    auth_mode = agents_config["agents"][agent_type].get("auth_mode", "iam")

    if auth_mode == "oauth":
        return AGENTS_AUTH.get(agent_type)

    return None


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
        auth_mode = agent_info.get("auth_mode", "iam")
        icon = "🔐" if auth_mode == "oauth" else "🔑"
        return f"{icon} {agent_info['name']}"

    selected_agent = st.radio(
        "Select Agent",
        all_agents,
        format_func=format_agent_name,
        key="agent_selector",
    )

    # Get selected agent's auth mode
    selected_agent_info = agents_config["agents"][selected_agent]
    auth_mode = selected_agent_info.get("auth_mode", "iam")
    agent_type = selected_agent

    # Show authentication status (minimal)
    if auth_mode == "oauth":
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
auth_mode = agents_config["agents"][agent_type].get("auth_mode", "iam")
current_agent_in_session = st.session_state.get("agent_type")

if auth_mode == "oauth" and current_agent_in_session != agent_type:
    # Show login form in main screen (left-aligned)
    agent_info = agents_config["agents"][agent_type]

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

                if not auth_config:
                    agent_name = agent_info.get("agent_name", agent_type)
                    st.error("❌ OAuth not configured for this agent")
                    st.caption(f"Missing SSM parameter: `/agentcore/{agent_name}/oauth-config`")
                else:
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
# MAIN SCREEN: Agent Interface (authenticated or IAM)
# ============================================================================

# Get agent config and use cases
agent_info = agents_config["agents"][agent_type]
use_cases = use_cases_config[agent_type]

# Title with agent name
st.title(agent_info['name'])

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
