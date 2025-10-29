import json
import logging
import os
import re
import time
import uuid
from pathlib import Path

import boto3
import requests
import streamlit as st
import yaml
from shared.auth_utils import authenticate, invoke_with_token
from utils import vision_utils

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_HEALTH_BADGES = True
ENABLE_VISION_CAPABILITY = True  # Image upload and analysis for supported agents

# ============================================================================
# INVOCATION MODES (priority order)
# ============================================================================
# 1. AGENTCORE_LOCAL_MODE env var → Local HTTP (./demo.sh --local)
# 2. oauth_config → AWS with JWT
# 3. Default → AWS with IAM
# ============================================================================

# Health check configuration
HEALTH_CONFIG = {
    "timeout": 5,
    "test_prompt": "ping",
    "local": {"color": "#10b981", "tooltip": "Connected to local environment"},
    "live": {"color": "#3b82f6", "tooltip": "Connected to live environment"},
    "error": {"color": "#ef4444", "tooltip": "Connection error"}
}


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


def get_agent_endpoint_url(agent_type: str) -> str | None:
    """Get endpoint_url from config or environment"""
    agent_cfg = agents_config["agents"][agent_type]
    if os.getenv("AGENTCORE_LOCAL_MODE"):
        local_port = agent_cfg.get("local_port", 8080)
        return f"http://localhost:{local_port}"
    return agent_cfg.get("endpoint_url")


def invoke_local_endpoint(endpoint_url: str, prompt: str, session_id: str, timeout: int, image_base64: str = None):
    """HTTP POST to local endpoint with streaming response"""
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": "streamlit-user",
    }

    # Add image if provided (vision capability)
    if image_base64:
        payload["image_base64"] = image_base64
        logger.info(f"[VISION DEBUG] Added image_base64 to payload (length: {len(image_base64)})")
    else:
        logger.info("[VISION DEBUG] No image_base64 to add to payload")

    logger.info(f"[VISION DEBUG] Payload keys being sent: {list(payload.keys())}")

    response = requests.post(
        f"{endpoint_url}/invocations",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def check_local_health(endpoint_url: str) -> tuple[bool, str, int | None]:
    """Check local endpoint health via /ping"""
    try:
        response = requests.get(
            f"{endpoint_url}/ping",
            timeout=HEALTH_CONFIG["timeout"]
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "Healthy":
                return True, "local", 200
        return False, "error", response.status_code
    except Exception:
        return False, "error", None


def check_aws_health(agent_info: dict, auth_config: dict | None, auth_token: str | None) -> tuple[bool, str, int | None]:
    """Check AWS endpoint health via /invocations endpoint.

    Note: AWS AgentCore Runtime does not expose a /ping endpoint (only local Docker does).
    We must use /invocations with a minimal prompt for health checks.
    """
    try:
        if auth_config and auth_token:
            logger.debug("AWS health check: Using OAuth/JWT authentication")
            response = invoke_with_token(
                agent_arn=agent_info["arn"],
                token=auth_token,
                prompt=HEALTH_CONFIG["test_prompt"],
                session_id="health-check",
                region=AWS_REGION,
                timeout=HEALTH_CONFIG["timeout"],
            )
            if response.status_code == 200:
                return True, "live", 200
            return False, "error", response.status_code
        else:
            logger.debug("AWS health check: Using IAM authentication")
            client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
            response = client.invoke_agent_runtime(
                agentRuntimeArn=agent_info["arn"],
                payload=json.dumps({"prompt": HEALTH_CONFIG["test_prompt"], "session_id": "health-check"}),
            )
            if response.get("response"):
                return True, "live", 200
            return False, "error", None
    except requests.exceptions.HTTPError as e:
        logger.debug(f"AWS health check HTTPError: {e}, status: {e.response.status_code if e.response else None}")
        return False, "error", e.response.status_code if e.response else None
    except Exception as e:
        logger.debug(f"AWS health check failed: {e}")
        return False, "error", None


def get_or_create_session_id(agent_type: str, username: str) -> str:
    """Get session ID from file or create new one"""
    sessions_dir = Path(__file__).parent / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    session_file = sessions_dir / f".{agent_type}_{username}"
    logger.info(f"[SESSION] Using session file: {session_file}")

    # Try to read existing session ID
    if session_file.exists():
        try:
            session_id = session_file.read_text().strip()
            if session_id and len(session_id) >= 33:  # AWS minimum
                logger.info(f"Loaded session ID for {agent_type}/{username}: {session_id}")
                return session_id
        except Exception as e:
            logger.warning(f"Failed to read session file: {e}")

    # Generate new session ID
    session_id = str(uuid.uuid4())

    # Save to file
    try:
        session_file.write_text(session_id)
        logger.info(f"Created new session ID for {agent_type}/{username}: {session_id}")
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

    # Run health check if needed (only for IAM agents or authenticated OAuth agents)
    current_agent_in_session = st.session_state.get("agent_type")
    is_oauth_agent = selected_agent_info.get("oauth_config") is not None
    is_authenticated = current_agent_in_session == agent_type

    if ENABLE_HEALTH_BADGES and (not is_oauth_agent or is_authenticated):
        health_key = f"health_status_{agent_type}"
        status_code_key = f"health_status_code_{agent_type}"

        # Run health check once if not already done
        if health_key not in st.session_state:
            try:
                local_endpoint = get_agent_endpoint_url(agent_type)
                if local_endpoint:
                    success, state, status_code = check_local_health(local_endpoint)
                else:
                    agent_auth_config = get_agent_auth_config(agent_type)
                    auth_token = st.session_state.get("auth_token") if agent_auth_config else None
                    success, state, status_code = check_aws_health(selected_agent_info, agent_auth_config, auth_token)
                st.session_state[health_key] = state
                st.session_state[status_code_key] = status_code
            except Exception:
                st.session_state[health_key] = "error"
                st.session_state[status_code_key] = None

    # Show authentication status (minimal)
    if selected_agent_info.get("oauth_config"):
        current_agent_in_session = st.session_state.get("agent_type")

        if current_agent_in_session == selected_agent:
            # User is logged in - show logout button
            st.markdown("")  # Spacer
            st.caption(f"Logged in as **{st.session_state.get('username', 'User')}**")
            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()

    st.markdown("---")

    # Footer
    st.caption("🏦 AWS GenAI Loft FinTech Event")
    st.caption("Built with Amazon Bedrock AgentCore")

    # Health status badge (if enabled)
    if ENABLE_HEALTH_BADGES and (not is_oauth_agent or is_authenticated):
        health_key = f"health_status_{agent_type}"
        status_code_key = f"health_status_code_{agent_type}"

        if health_key in st.session_state:
            status = st.session_state[health_key]
            status_code = st.session_state.get(status_code_key)
            config = HEALTH_CONFIG[status]
            status_text = "Healthy" if status != "error" else "Connection error"

            # Build tooltip with status code if available
            tooltip = config["tooltip"]
            if status == "error" and status_code:
                tooltip = f"{tooltip} (HTTP {status_code})"

            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; margin: 0.5rem 0;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background: {config['color']}; flex-shrink: 0;"
                         title="{tooltip}"></div>
                    <span style="font-size: 0.875rem; color: #6b7280;">Status: {status_text}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

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
local_endpoint = get_agent_endpoint_url(agent_type)

# Agent title
st.title(agent_info['name'])

# Initialize session state for this agent
# Each agent gets its own message history and session ID
username = st.session_state.get("username", "anonymous")
messages_key = f"messages_{agent_type}_{username}"
session_id_key = f"session_id_{agent_type}_{username}"

if messages_key not in st.session_state:
    st.session_state[messages_key] = []

if session_id_key not in st.session_state:
    st.session_state[session_id_key] = get_or_create_session_id(agent_type, username)

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

                # Handle error events from the agent
                elif isinstance(event, dict) and "error" in event:
                    error_type = event.get("error_type", "Unknown")
                    error_msg = event.get("message", event.get("error", "Unknown error"))
                    logger.error(f"Agent error: {error_type} - {error_msg}")
                    # Display error to user using a formatted error message
                    yield f"\n\n**⚠️ Agent Error ({error_type}):**\n\n{error_msg}\n\n"

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


prompt = st.chat_input(
    "Type your message here...",
    accept_file=True if (ENABLE_VISION_CAPABILITY and vision_utils.should_enable_vision(agent_type, agents_config)) else False,
    file_type=["png", "jpg", "jpeg"] if (ENABLE_VISION_CAPABILITY and vision_utils.should_enable_vision(agent_type, agents_config)) else None,
)

if prompt:
    prompt_text = prompt.text if hasattr(prompt, 'text') else prompt
    uploaded_files = prompt.files if hasattr(prompt, 'files') else []
    uploaded_file = uploaded_files[0] if uploaded_files else None

    logger.info(f"[VISION DEBUG] uploaded_files count: {len(uploaded_files)}")
    logger.info(f"[VISION DEBUG] uploaded_file is None: {uploaded_file is None}")
    if uploaded_file:
        logger.info(f"[VISION DEBUG] File name: {uploaded_file.name}, size: {len(uploaded_file.getvalue())} bytes")

    session_id = st.session_state[session_id_key]

    image_base64 = None
    if ENABLE_VISION_CAPABILITY and uploaded_file:
        image_base64 = vision_utils.process_image_to_base64(uploaded_file)
        logger.info(f"[VISION DEBUG] image_base64 is None: {image_base64 is None}")
        if image_base64:
            logger.info(f"[VISION DEBUG] image_base64 length: {len(image_base64)} chars")
        if image_base64 is None:
            st.stop()

    with st.chat_message("user"):
        st.markdown(prompt_text)
        if ENABLE_VISION_CAPABILITY and uploaded_file:
            vision_utils.render_attached_image_in_chat(uploaded_file)

    st.session_state[messages_key].append({"role": "user", "content": prompt_text})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        tool_placeholder = st.empty()  # For tool execution messages

        try:
            logger.info(f"Starting agent invocation for agent_type: {agent_type}")

            # Brief spinner only for API connection
            with st.spinner("Connecting to agent..."):
                logger.info(f"Using session ID: {session_id}")

                agent_auth_config = get_agent_auth_config(agent_type)

                if local_endpoint:
                    logger.info(f"Using endpoint: {local_endpoint}")

                    response = invoke_local_endpoint(
                        endpoint_url=local_endpoint,
                        prompt=prompt_text,
                        session_id=session_id,
                        timeout=TIMEOUT_SECONDS,
                        image_base64=image_base64,
                    )

                elif agent_auth_config:
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
                            prompt=prompt_text,
                            session_id=session_id,
                            region=AWS_REGION,
                            timeout=TIMEOUT_SECONDS,
                            image_base64=image_base64,
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
                    logger.info("Using IAM authentication with boto3")

                    client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
                    logger.info(
                        f"Created bedrock-agentcore client for region: {AWS_REGION}"
                    )

                    payload_dict = {"prompt": prompt_text, "session_id": session_id}
                    if image_base64:
                        payload_dict["image_base64"] = image_base64
                        logger.info(f"Image included in IAM payload (size: {len(image_base64)} bytes)")

                    response = client.invoke_agent_runtime(
                        agentRuntimeArn=agent_info["arn"],
                        payload=json.dumps(payload_dict),
                    )

                    logger.info(
                        "Agent invocation successful (IAM), processing event stream"
                    )

            # Stream response
            # For local/authenticated/HTTP: response is already the stream
            # For IAM/boto3: response["response"] is the stream
            response_stream = response if (local_endpoint or agent_auth_config) else response["response"]

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

                    # Sync health status to healthy after successful invocation
                    if ENABLE_HEALTH_BADGES:
                        health_key = f"health_status_{agent_type}"
                        status_code_key = f"health_status_code_{agent_type}"
                        state = "local" if local_endpoint else "live"
                        st.session_state[health_key] = state
                        st.session_state[status_code_key] = 200
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
