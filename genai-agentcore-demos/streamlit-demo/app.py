import streamlit as st
import boto3
import json
import time

# Configuration
TIMEOUT_SECONDS = 30  # REQ-014

# Agent configuration (REQ-024, REQ-025, REQ-026)
AGENTS = {
    "Finance": {
        "arn": "arn:aws:bedrock-agentcore:us-west-2:905418344519:runtime/personal_finance_agent-4EJMkjFcLO",
        "query": "I make $180K with $4K monthly expenses. Create my 50/30/20 budget and analyze if I'm overspending on dining at $1200/month"
    },
    "Market": {
        "arn": "arn:aws:bedrock-agentcore:us-west-2:905418344519:runtime/market_trends_agent-VuvnWl6Gkp",
        "query": "Compare NVDA, MSFT, and GOOGL over 6 months and create a $50K growth portfolio for a tech professional"
    }
}

# Page configuration
st.set_page_config(
    page_title="AWS AgentCore FinTech Demo",
    page_icon="🏦",
    layout="centered"
)

# Title (REQ-001)
st.title("🏦 AWS AgentCore FinTech Demo")

# AWS connectivity verification
try:
    # Use default session (picks up AWS_PROFILE env var)
    sts = boto3.client('sts', region_name='us-west-2')
    identity = sts.get_caller_identity()
    st.success(f"✅ AWS Connected: {identity['Arn']}")
except Exception as e:
    st.error(f"❌ AWS Connection Failed: {str(e)}")
    st.info("Set AWS_PROFILE environment variable or configure credentials")

# Tab selector (REQ-004, REQ-002)
tab = st.radio("Select Agent:", ["Finance", "Market"], horizontal=True)

# Persona display (REQ-003)
st.info("👤 Sarah Chen | $180K | Tech Professional | SF")

# Demo button (REQ-006, REQ-007, REQ-027)
if st.button("Run Demo Scenario", type="primary"):
    with st.spinner("Agent thinking..."):  # REQ-016
        try:
            # Create AgentCore client (REQ-023)
            client = boto3.client("bedrock-agentcore", region_name="us-west-2")

            # Get agent config for selected tab
            agent_config = AGENTS[tab]

            # Invoke agent (REQ-006, REQ-007)
            response = client.invoke_agent_runtime(
                agentRuntimeArn=agent_config["arn"],
                payload=json.dumps({"prompt": agent_config["query"]})
            )

            # Stream response (REQ-008, REQ-009, REQ-010)
            with st.chat_message("assistant"):
                response_buffer = ""
                start_time = time.time()

                for line in response["response"].iter_lines():
                    # Check timeout (REQ-014)
                    if time.time() - start_time > TIMEOUT_SECONDS:
                        st.warning("⏱️ Response timeout. Please try again.")
                        break

                    if line.startswith(b"data: "):
                        try:
                            # Robust JSON parsing (REQ-015)
                            token = json.loads(line[6:])

                            # AgentCore streams text tokens directly as JSON strings
                            if isinstance(token, str):
                                response_buffer += token

                        except json.JSONDecodeError:
                            # Skip malformed events (REQ-015)
                            continue

                # Display complete response (REQ-019)
                if response_buffer:
                    st.markdown(response_buffer)

        except Exception as e:
            # Simple error handling (REQ-013)
            st.error("Connection failed. Please try again.")
