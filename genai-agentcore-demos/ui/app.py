import json
import logging
import os
import random
import re
import time
import uuid
from pathlib import Path

import boto3
import requests
import streamlit as st
import yaml
from libs.python.auth_utils import authenticate, invoke_with_token
from utils import document_utils, vision_utils

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
# AGENT NAME EMOJI MAPPING
# ============================================================================
# Universal emoji list for all agents (finance + smart AI mix)
AGENT_EMOJIS = [
    "💰",
    "💼",
    "📊",
    "📈",
    "🏦",
    "💹",
    "⚡️",
    "🌟",
]


def get_agent_display_name(agent_type: str, base_name: str) -> str:
    """Add a random emoji prefix to agent name"""
    emoji = random.choice(AGENT_EMOJIS)
    return f"{emoji} {base_name}"


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
    "error": {"color": "#ef4444", "tooltip": "Connection error"},
}


# Load configuration files
@st.cache_resource
def load_config():
    """
    Load agent configurations with SSM auto-discovery.

    Loads static config from YAML (name, capabilities) and merges with
    runtime config from SSM (ARN, OAuth config).
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from libs.python.ssm_utils import get_all_agent_configs

    config_dir = Path(__file__).parent / "config"

    # Load static config from YAML
    with open(config_dir / "agents.yaml", "r") as f:
        static_config = yaml.safe_load(f)

    # Get runtime config from SSM (ARN + OAuth)
    region = static_config["aws"]["region"]
    runtime_configs = get_all_agent_configs(region=region)

    # Merge runtime config into static config
    for agent_name, runtime_config in runtime_configs.items():
        if agent_name in static_config["agents"]:
            static_config["agents"][agent_name]["arn"] = runtime_config["arn"]
            static_config["agents"][agent_name]["oauth_config"] = runtime_config.get(
                "oauth_config"
            )
            logger.debug(f"Merged SSM config for agent: {agent_name}")

    return static_config


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


def invoke_local_endpoint(
    endpoint_url: str,
    prompt: str,
    session_id: str,
    timeout: int,
    image_base64: str = None,
    document_base64: str = None,
    filename: str = None,
):
    """HTTP POST to local endpoint with streaming response"""
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": "streamlit-user",
    }

    # Add image if provided (vision capability)
    if image_base64:
        payload["image_base64"] = image_base64
        logger.info(
            f"[VISION DEBUG] Added image_base64 to payload (length: {len(image_base64)})"
        )

    # Add document if provided (PDF/CSV support)
    if document_base64 and filename:
        payload["document_base64"] = document_base64
        payload["filename"] = filename
        logger.info(
            f"[DOCUMENT] Added document to payload: {filename} (length: {len(document_base64)})"
        )

    logger.info(f"[DOCUMENT] Payload keys being sent: {list(payload.keys())}")

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
            f"{endpoint_url}/ping", timeout=HEALTH_CONFIG["timeout"]
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "Healthy":
                return True, "local", 200
        return False, "error", response.status_code
    except Exception:
        return False, "error", None


def check_aws_health(
    agent_info: dict, auth_config: dict | None, auth_token: str | None
) -> tuple[bool, str, int | None]:
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
                payload=json.dumps(
                    {
                        "prompt": HEALTH_CONFIG["test_prompt"],
                        "session_id": "health-check",
                    }
                ),
            )
            if response.get("response"):
                return True, "live", 200
            return False, "error", None
    except requests.exceptions.HTTPError as e:
        logger.debug(
            f"AWS health check HTTPError: {e}, status: {e.response.status_code if e.response else None}"
        )
        return False, "error", e.response.status_code if e.response else None
    except Exception as e:
        logger.debug(f"AWS health check failed: {e}")
        return False, "error", None


def create_new_session_id() -> str:
    """Generate a new session ID for fresh conversations"""
    session_id = str(uuid.uuid4())
    logger.info(f"Created new session ID: {session_id}")
    return session_id


def clear_session_file(agent_type: str, username: str):
    """Remove persisted session file on logout"""
    sessions_dir = Path(__file__).parent / "sessions"
    session_file = sessions_dir / f".{agent_type}_{username}"

    if session_file.exists():
        try:
            session_file.unlink()
            logger.info(f"Cleared session file for {agent_type}/{username}")
        except Exception as e:
            logger.warning(f"Failed to clear session file: {e}")


# Page configuration
st.set_page_config(
    page_title="AWS AgentCore FinTech Demo", page_icon="🏦", layout="centered"
)

# Custom CSS to reduce sidebar padding for better footer visibility
st.markdown(
    """
    <style>
    /* Reduce sidebar padding */
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* Reduce spacing between sidebar elements */
    section[data-testid="stSidebar"] .element-container {
        margin-bottom: 0.5rem !important;
    }

    /* Reduce markdown spacing in sidebar */
    section[data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0.5rem !important;
    }

    /* Reduce horizontal rule spacing */
    section[data-testid="stSidebar"] hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar with configuration
with st.sidebar:
    # ============================================================================
    # SECTION 0: Agent Title
    # ============================================================================
    # Determine active agent (logged in agent or selected agent)
    all_agents = list(agents_config["agents"].keys())
    current_agent_in_session = st.session_state.get("agent_type")

    logger.info(f"--- RERUN START ---")
    logger.info(f"Session State Keys: {list(st.session_state.keys())}")
    logger.info(f"current_agent_in_session: {current_agent_in_session}")
    logger.info(f"agent_selector_value: {st.session_state.get('agent_selector_value')}")

    if current_agent_in_session:
        # User is logged in - show logged-in agent
        agent_type = current_agent_in_session
        logger.info(f"User logged in. agent_type set to: {agent_type}")
    else:
        # Not logged in - show selected agent
        agent_type = st.session_state.get("agent_selector_value", all_agents[0])
        logger.info(f"User NOT logged in. agent_type set to: {agent_type}")

    agent_info_for_title = agents_config["agents"][agent_type]

    # Display agent title at top of sidebar
    st.markdown(
        f"### {get_agent_display_name(agent_type, agent_info_for_title['name'])}"
    )
    st.markdown("---")

    # ============================================================================
    # SECTION 1: Connection Status
    # ============================================================================
    # AWS connectivity verification
    if not os.getenv("AGENTCORE_LOCAL_MODE"):
        try:
            sts = boto3.client("sts", region_name=AWS_REGION)
            identity = sts.get_caller_identity()
            st.success("✅ AWS Connected")
        except Exception:
            st.error("❌ AWS Not Connected")
            st.caption("Set AWS_PROFILE or configure credentials")
            st.stop()
    else:
        st.success("✅ Local Mode")

    # Get selected agent config (needed for health check)
    selected_agent = st.session_state.get("agent_selector_value", all_agents[0])
    selected_agent_info = agents_config["agents"][selected_agent]

    # Run health check if needed (only for IAM agents or authenticated OAuth agents)
    current_agent_in_session = st.session_state.get("agent_type")
    is_oauth_agent = selected_agent_info.get("oauth_config") is not None
    is_authenticated = current_agent_in_session == selected_agent

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
                    auth_token = (
                        st.session_state.get("auth_token")
                        if agent_auth_config
                        else None
                    )
                    success, state, status_code = check_aws_health(
                        selected_agent_info, agent_auth_config, auth_token
                    )
                st.session_state[health_key] = state
                st.session_state[status_code_key] = status_code
            except Exception:
                st.session_state[health_key] = "error"
                st.session_state[status_code_key] = None

        # Display health status badge (below AWS Connected with extra margin)
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
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 1rem;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background: {config["color"]}; flex-shrink: 0;"
                         title="{tooltip}"></div>
                    <span style="font-size: 0.875rem; color: #6b7280;">Status: {status_text}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ============================================================================
    # SECTION 2: Agent Selection & Authentication
    # ============================================================================
    # Check if user is logged into an OAuth agent
    current_agent_in_session = st.session_state.get("agent_type")

    # Track if we show any content in this section (for separator logic)
    show_section_separator = False

    if current_agent_in_session:
        # User is logged in - show only logout section
        st.caption(f"Logged in as **{st.session_state.get('username', 'User')}**")
        if st.button("Logout", use_container_width=True):
            # Get current user info before clearing
            username = st.session_state.get("username")
            agent_type = st.session_state.get("agent_type")

            # Clear session files (if any)
            if username and agent_type:
                clear_session_file(agent_type, username)

            # Clear session state
            st.session_state.clear()
            st.rerun()
        show_section_separator = True

        # Set agent_type from logged-in session
        agent_type = current_agent_in_session
        selected_agent_info = agents_config["agents"][agent_type]
    else:
        # Not logged in - show agent selector (only if multiple agents available)
        if len(all_agents) == 1:
            # Only one agent - auto-select without showing selector
            selected_agent = all_agents[0]
            show_section_separator = False
        else:
            # Multiple agents - show selector
            def format_agent_name(agent_key: str) -> str:
                agent_info = agents_config["agents"][agent_key]
                icon = "🔐" if agent_info.get("oauth_config") else "🔑"
                display_name = get_agent_display_name(agent_key, agent_info["name"])
                return f"{icon} {display_name}"

            # Determine default selection index from session state
            # Priority:
            # 1. Current widget state (agent_selector) - handles immediate user interaction
            # 2. Persisted value (agent_selector_value) - handles page reloads/navigation
            # 3. Default (first agent)
            current_selection = st.session_state.get("agent_selector")
            persisted_selection = st.session_state.get("agent_selector_value")
            default_agent = current_selection or persisted_selection or all_agents[0]
            try:
                default_index = all_agents.index(default_agent)
            except ValueError:
                default_index = 0

            selected_agent = st.radio(
                "Select Agent",
                all_agents,
                index=default_index,
                format_func=format_agent_name,
                key="agent_selector",
            )
            show_section_separator = True

        # Update session state for health check tracking
        st.session_state["agent_selector_value"] = selected_agent

        # Get selected agent config
        selected_agent_info = agents_config["agents"][selected_agent]
        agent_type = selected_agent

        # Auto-login for agents that don't require OAuth (IAM only)
        if not selected_agent_info.get("oauth_config"):
            st.session_state["username"] = "guest"
            st.session_state["agent_type"] = selected_agent
            st.rerun()

    # Only show separator if we displayed content in this section
    if show_section_separator:
        st.markdown("---")

    # ============================================================================
    # SECTION 3: Footer
    # ============================================================================
    st.caption("🏦 AWS GenAI Loft 2025")
    st.caption("Built with ❤️ by binbash team.")

# ============================================================================
# MAIN SCREEN: Authentication Gate (for OAuth agents)
# ============================================================================
# Check if selected agent requires OAuth and user is not logged in
agent_info = agents_config["agents"][agent_type]
current_agent_in_session = st.session_state.get("agent_type")

if agent_info.get("oauth_config") and current_agent_in_session != agent_type:
    # Show login form in main screen (left-aligned)
    # Single clean title with agent name
    st.title(get_agent_display_name(agent_type, agent_info["name"]))
    st.markdown("")

    # Left-aligned login form (max width to match title)
    with st.form(f"login_form_{agent_type}", clear_on_submit=False):
        st.markdown("Please enter your credentials to continue:")
        st.markdown("")

        username = st.text_input(
            "Username", placeholder="broker_demo", key=f"username_input_{agent_type}"
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="DemoPass123!",
            key=f"password_input_{agent_type}",
        )

        st.markdown("")
        submit = st.form_submit_button(
            "Login", use_container_width=True, type="primary"
        )

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
                        access_token = auth_result["AccessToken"]
                        st.session_state["auth_token"] = access_token
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def escape_latex_chars(text):
    """
    Escape characters that trigger LaTeX rendering in Streamlit.
    Prevents "$1,200 per month" from being interpreted as LaTeX math mode.
    """
    # Escape dollar signs to prevent LaTeX interpretation
    text = re.sub(r"\$", r"\\$", text)
    return text


def clean_agent_response(text):
    """
    Remove XML tags from agent responses (thinking, options).
    Used for displaying messages from chat history.
    """
    if not text:
        return text
    # Remove thinking tags
    text = re.sub(r"<thinking>(.*?)</thinking>", "", text, flags=re.DOTALL)
    # Remove options tags
    text = re.sub(r"<options>(.*?)</options>", "", text, flags=re.DOTALL)
    return text.strip()


def render_option_buttons(options_list, agent_type, message_idx):
    """
    Render option buttons for a message.
    Uses message index for stable button keys across reruns.

    Args:
        options_list: List of option strings to display as buttons
        agent_type: Current agent type for session state key
        message_idx: Index of this message in history (for stable keys)
    """
    if not options_list:
        return

    # Custom CSS to align button text to the left
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] p {
            text-align: left !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Stack buttons vertically (one per row)
    for idx, option in enumerate(options_list):
        # Key uses message_idx (stable) instead of message count (unstable)
        if st.button(
            option,
            key=f"opt_{agent_type}_msg{message_idx}_opt{idx}",
            use_container_width=True,
        ):
            st.session_state[f"selected_option_{agent_type}"] = option
            st.rerun()


# Generator function for st.write_stream()
def stream_agent_response(response_stream, tool_placeholder, timeout_seconds):
    """
    Generator that yields tokens from AgentCore stream.
    Handles tool messages as side effects.
    Ensures markdown headers start on their own line.
    """
    start_time = time.time()
    prev_char = ""  # Track last character from previous token for header formatting
    tokens_yielded = (
        False  # Track if we've yielded any tokens to avoid duplication on final event
    )

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

                # Debug: Log raw event data to see options
                if isinstance(event, str) and "<option" in event.lower():
                    logger.info(
                        f"[OPTIONS DEBUG STREAM] Found option in string event: {event[:100]}"
                    )
                elif (
                    isinstance(event, dict)
                    and event.get("token")
                    and "<option" in event.get("token", "").lower()
                ):
                    logger.info(
                        f"[OPTIONS DEBUG STREAM] Found option in token: {event.get('token')[:100]}"
                    )

                # Handle tool messages (side effect - updates UI)
                if isinstance(event, dict) and event.get("type") == "thinking":
                    tool_msg = event.get("message", "")
                    if tool_msg:
                        tool_placeholder.caption(f"🔧 {tool_msg}")
                        logger.info(f"Tool: {tool_msg}")

                # Handle error events from the agent
                elif isinstance(event, dict) and "error" in event:
                    error_type = event.get("error_type", "Unknown")
                    error_msg = event.get(
                        "message", event.get("error", "Unknown error")
                    )
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
                        tokens_yielded = True

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
                        tokens_yielded = True

                elif isinstance(event, dict) and event.get("type") == "final":
                    result = event.get("result", "")
                    logger.info(
                        f"FINAL EVENT: result length={len(result)}, contains #={('#' in result)}"
                    )
                    if result and not tokens_yielded:
                        logger.info("Yielding final result as no tokens were streamed")
                        yield result
                    elif result and tokens_yielded:
                        logger.info("Skipping final result yield to avoid duplication")

            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {e}")
                continue


# Agent title
st.title(get_agent_display_name(agent_type, agent_info["name"]))

# Initialize session state for this agent
# Each agent gets its own message history and session ID
username = st.session_state.get("username", "anonymous")
messages_key = f"messages_{agent_type}_{username}"
session_id_key = f"session_id_{agent_type}_{username}"

if messages_key not in st.session_state:
    st.session_state[messages_key] = []

if session_id_key not in st.session_state:
    # Create fresh session ID for each login (not persisted across logins)
    st.session_state[session_id_key] = create_new_session_id()

# Display chat messages from history
for msg_idx, message in enumerate(st.session_state[messages_key]):
    with st.chat_message(message["role"]):
        # Clean any XML tags from historical messages (defensive cleanup)
        cleaned_content = (
            clean_agent_response(message["content"])
            if message["role"] == "assistant"
            else message["content"]
        )
        st.markdown(cleaned_content)

        # Render option buttons if this message has options metadata
        if (
            message["role"] == "assistant"
            and "options" in message
            and message["options"]
        ):
            render_option_buttons(message["options"], agent_type, msg_idx)


# Check for selected option (from button click)
selected_option_key = f"selected_option_{agent_type}"
if selected_option_key in st.session_state:
    prompt = st.session_state[selected_option_key]
    del st.session_state[selected_option_key]  # Clear after reading
else:
    # Check if agent supports file uploads (vision for images, documents for PDF/CSV)
    supports_vision = ENABLE_VISION_CAPABILITY and vision_utils.should_enable_vision(
        agent_type, agents_config
    )
    supports_documents = document_utils.should_enable_documents(
        agent_type, agents_config
    )
    accepts_files = supports_vision or supports_documents

    # Determine allowed file types
    allowed_types = []
    if supports_vision:
        allowed_types.extend(["png", "jpg", "jpeg"])
    if supports_documents:
        allowed_types.extend(["pdf", "csv"])

    prompt = st.chat_input(
        "Type your message here...",
        accept_file=accepts_files,
        file_type=allowed_types if allowed_types else None,
    )

if prompt:
    logger.info("[OPTIONS DEBUG] ===== NEW MESSAGE HANDLER START =====")
    prompt_text = prompt.text if hasattr(prompt, "text") else prompt
    uploaded_files = prompt.files if hasattr(prompt, "files") else []
    uploaded_file = uploaded_files[0] if uploaded_files else None

    logger.info(f"[VISION DEBUG] uploaded_files count: {len(uploaded_files)}")
    logger.info(f"[VISION DEBUG] uploaded_file is None: {uploaded_file is None}")
    if uploaded_file:
        logger.info(
            f"[VISION DEBUG] File name: {uploaded_file.name}, size: {len(uploaded_file.getvalue())} bytes"
        )

    session_id = st.session_state[session_id_key]

    image_base64 = None
    document_base64 = None
    filename = None

    if uploaded_file:
        file_type = document_utils.get_file_type_from_name(uploaded_file.name)
        logger.info(
            f"[DOCUMENT] Uploaded file type: {file_type}, name: {uploaded_file.name}"
        )

        if file_type == "image":
            # Process as image (existing vision capability)
            image_base64 = vision_utils.process_image_to_base64(uploaded_file)
            if image_base64 is None:
                st.stop()
        elif file_type in ["pdf", "csv"]:
            # Process as document (new multi-format support)
            result = document_utils.process_document_to_base64(uploaded_file)
            if result:
                document_base64, filename = result
            else:
                st.stop()

    with st.chat_message("user"):
        st.markdown(prompt_text)
        if uploaded_file:
            file_type = document_utils.get_file_type_from_name(uploaded_file.name)
            document_utils.render_attached_document_in_chat(uploaded_file, file_type)

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
                        document_base64=document_base64,
                        filename=filename,
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
                            document_base64=document_base64,
                            filename=filename,
                        )
                        logger.info(
                            "Agent invocation successful (authenticated), processing event stream"
                        )

                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 401:
                            st.error(
                                "Authentication token expired. Please login again."
                            )
                            # Get user info before clearing
                            username = st.session_state.get("username")
                            agent_type_val = st.session_state.get("agent_type")

                            # Clear session files and state
                            if username and agent_type_val:
                                clear_session_file(agent_type_val, username)
                            st.session_state.clear()
                            st.rerun()
                        else:
                            raise

                else:
                    logger.info("Using IAM authentication with boto3")

                    client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
                    logger.info(
                        f"Created bedrock-agentcore client for region: {AWS_REGION}"
                    )

                    # For IAM mode: use 'anonymous' actor_id for memory isolation
                    # (No OAuth login, so no username available)
                    actor_id = "anonymous"

                    payload_dict = {
                        "prompt": prompt_text,
                        "session_id": session_id,
                        "actor_id": actor_id,  # Pass actor_id in payload
                    }
                    if image_base64:
                        payload_dict["image_base64"] = image_base64
                        logger.info(
                            f"Image included in IAM payload (size: {len(image_base64)} bytes)"
                        )

                    if document_base64 and filename:
                        payload_dict["document_base64"] = document_base64
                        payload_dict["filename"] = filename
                        logger.info(
                            f"Document included in IAM payload: {filename} (size: {len(document_base64)} bytes)"
                        )

                    logger.info(f"IAM mode: Using actor_id='{actor_id}'")

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
            response_stream = (
                response
                if (local_endpoint or agent_auth_config)
                else response["response"]
            )

            logger.info("[OPTIONS DEBUG] About to start streaming response")

            # Accumulate response text manually (st.write_stream returns None)
            message_placeholder = st.empty()
            response_text = ""
            token_count = 0
            for token in stream_agent_response(
                response_stream, tool_placeholder, TIMEOUT_SECONDS
            ):
                response_text += token
                token_count += 1
                message_placeholder.markdown(response_text + "▌")

            logger.info(
                f"[OPTIONS DEBUG] Loop ended, processed {token_count} tokens, total {len(response_text)} chars"
            )

            # Post-process: Extract thinking content and options, then clean display
            if response_text and response_text.strip():
                logger.info("[OPTIONS DEBUG] Entering post-process block")
                logger.info(
                    f"[OPTIONS DEBUG] Full response length: {len(response_text)}"
                )
                logger.info(
                    f"[OPTIONS DEBUG] Response preview: {response_text[:200]}..."
                )

                # Extract thinking content using regex
                thinking_pattern = r"<thinking>(.*?)</thinking>"
                thinking_matches = re.findall(
                    thinking_pattern, response_text, re.DOTALL
                )

                # Extract options content using regex
                options_pattern = r"<options>(.*?)</options>"
                options_matches = re.findall(options_pattern, response_text, re.DOTALL)
                logger.info(
                    f"[OPTIONS DEBUG] Found {len(options_matches)} options blocks"
                )

                if options_matches:
                    logger.info(
                        f"[OPTIONS DEBUG] Options block content: {options_matches[0][:300]}"
                    )

                # Remove thinking and options tags from main response
                cleaned_response = re.sub(
                    thinking_pattern, "", response_text, flags=re.DOTALL
                )
                cleaned_response = re.sub(
                    options_pattern, "", cleaned_response, flags=re.DOTALL
                ).strip()
                logger.info(
                    f"[OPTIONS DEBUG] Cleaned response length: {len(cleaned_response)}"
                )

                # Update placeholder with cleaned response (removes XML tags)
                message_placeholder.markdown(cleaned_response)

                # Display thinking in expander if found
                if thinking_matches:
                    thinking_content = "\n\n".join(thinking_matches)
                    with st.expander("💭 Thinking Process", expanded=False):
                        st.text(thinking_content.strip())

                # Parse individual <option> tags
                options_list = []
                if options_matches:
                    option_pattern = r"<option>(.*?)</option>"
                    options_list = re.findall(
                        option_pattern, options_matches[0], re.DOTALL
                    )
                    options_list = [opt.strip() for opt in options_list if opt.strip()]
                    logger.info(
                        f"[OPTIONS DEBUG] Parsed {len(options_list)} individual options"
                    )
                    logger.info(f"[OPTIONS DEBUG] Options list: {options_list}")

                # Display option buttons if found (will also be rendered from history on rerun)
                if options_list:
                    msg_idx = len(
                        st.session_state[messages_key]
                    )  # Index for this new message
                    render_option_buttons(options_list, agent_type, msg_idx)

                # Add assistant response to chat history with options metadata
                if cleaned_response:
                    message_data = {"role": "assistant", "content": cleaned_response}
                    if options_list:
                        message_data["options"] = options_list
                    st.session_state[messages_key].append(message_data)
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
            st.session_state[messages_key].append(
                {"role": "assistant", "content": error_message}
            )
