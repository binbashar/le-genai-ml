import json
import logging
import re
import time
import uuid
from pathlib import Path

import boto3
import streamlit as st
import yaml

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    st.markdown("### Agent Selection")

    # Agent selector
    agent_type = st.radio(
        "Select Agent:",
        ["finance_assistant", "market_trends"],
        format_func=lambda x: agents_config["agents"][x]["name"],
        label_visibility="collapsed",
    )

    st.markdown("---")
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
            # Create Bedrock AgentCore client
            client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
            logger.info(f"Created bedrock-agentcore client for region: {AWS_REGION}")

            # Generate unique session ID
            session_id = str(uuid.uuid4())
            logger.info(f"Generated session ID: {session_id}")

            # Invoke agent runtime
            response = client.invoke_agent_runtime(
                agentRuntimeArn=agent_info["arn"],
                payload=json.dumps({"prompt": custom_prompt, "session_id": session_id}),
            )

            logger.info("Agent invocation successful, processing event stream")

        # Stream response to temporary placeholder
        with temp_placeholder.container():
            response_text = st.write_stream(
                stream_agent_response(
                    response["response"], tool_placeholder, TIMEOUT_SECONDS
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
