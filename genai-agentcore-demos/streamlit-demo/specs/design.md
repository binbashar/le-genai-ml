# Design Document
## AWS AgentCore FinTech Demo - Technical Design

### 1. Architecture Overview

```
Streamlit UI → boto3 Client → AgentCore API
                                ↓
                            SSE Response Stream
                                ↓
                        Parse & Display in Real-time
```

### 2. Design Principles

1. **Simplicity First**: Minimal code, maximum reliability
2. **No Abstractions**: Direct implementation only
3. **Fail Fast**: Simple errors, no retry logic
4. **Hard-coded Config**: Demo reliability over flexibility

### 3. Implementation Structure

```
streamlit-demo/
├── app.py           # Entire application (~50-100 lines)
├── pyproject.toml   # Dependencies
└── README.md        # Quick setup guide
```

### 4. Core Implementation Pattern

#### 4.1 Configuration
```python
# Hard-coded for reliability (REQ-024, REQ-025, REQ-026)
AGENTS = {
    "Finance": {
        "arn": "arn:aws:bedrock:us-west-2:XXX:agent/finance",
        "query": "I make $180K with $4K monthly expenses..."
    },
    "Market": {
        "arn": "arn:aws:bedrock:us-west-2:XXX:agent/market",
        "query": "Compare NVDA, MSFT, and GOOGL..."
    }
}
```

#### 4.2 UI Structure
```python
# Simple layout (REQ-001, REQ-002, REQ-003, REQ-027)
st.title("🏦 AWS AgentCore FinTech Demo")
tab = st.radio("Select Agent:", ["Finance", "Market"], horizontal=True)
st.info("👤 Sarah Chen | $180K | Tech Professional | SF")
```

#### 4.3 Streaming Handler
```python
# Direct SSE parsing (REQ-008, REQ-009, REQ-010)
with st.chat_message("assistant"):
    for line in response["response"].iter_lines():
        if line.startswith(b"data: "):
            event = json.loads(line[6:])

            if event.get("type") == "thinking":
                # Tool message (REQ-011, REQ-012)
                st.caption(f"🔧 {event.get('message', '')}")

            elif event.get("type") == "stream_token":
                # Response token (REQ-009)
                st.write(event.get("token", ""), end="")
```

#### 4.4 Agent Invocation
```python
# Simple boto3 call (REQ-006, REQ-007, REQ-023)
if st.button("Run Demo Scenario", type="primary"):
    with st.spinner("Agent thinking..."):  # REQ-016
        client = boto3.client("bedrock-agentcore", region_name="us-west-2")

        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENTS[tab]["arn"],
            payload=json.dumps({"prompt": AGENTS[tab]["query"]})
        )

        # Stream response
        parse_and_display(response)
```

### 5. Error Handling Strategy

```python
# Minimal error handling (REQ-013, REQ-014, REQ-015)
try:
    # Agent call
except Exception as e:
    st.error("Connection failed. Please try again.")
```

### 6. Dependencies

```toml
# pyproject.toml
[project]
name = "agentcore-fintech-demo"
requires-python = ">=3.13"
dependencies = [
    "streamlit==1.32.0",
    "boto3==1.34.0",
]
```

### 7. State Management

- No session state (stateless operation)
- Button enables/disables based on execution
- No history or persistence

### 8. Performance Considerations

- Direct streaming without buffering
- Single container for tool messages
- No complex state management
- Minimal UI updates

### 9. Complete Minimal Implementation

```python
# Complete app.py (~50 lines)
import streamlit as st
import boto3
import json

st.title("🏦 AWS AgentCore FinTech Demo")

# Config
AGENTS = {
    "Finance": ("arn:...", "I make $180K..."),
    "Market": ("arn:...", "Compare NVDA...")
}

# UI
tab = st.radio("Select:", ["Finance", "Market"], horizontal=True)
st.info("👤 Sarah Chen | $180K | Tech | SF")

if st.button("Run Demo", type="primary"):
    with st.spinner("Processing..."):
        try:
            # Call agent
            client = boto3.client("bedrock-agentcore", region="us-west-2")
            arn, query = AGENTS[tab]

            response = client.invoke_agent_runtime(
                agentRuntimeArn=arn,
                payload=json.dumps({"prompt": query})
            )

            # Stream response
            with st.chat_message("assistant"):
                for line in response["response"].iter_lines():
                    if line.startswith(b"data: "):
                        event = json.loads(line[6:])

                        if event.get("type") == "thinking":
                            st.caption(f"🔧 {event.get('message')}")
                        elif event.get("type") == "stream_token":
                            st.write(event.get("token", ""), end="")

        except Exception as e:
            st.error("Connection failed. Please try again.")
```

### 10. Testing Approach

Manual testing only:
1. Run Finance demo → Verify tools and response
2. Run Market demo → Verify tools and response
3. Test error case → Disconnect network

### 11. Key Design Decisions

| Decision | Rationale | Requirement |
|----------|-----------|-------------|
| Single file | Maximum simplicity | General principle |
| No error details | Avoid confusion | REQ-013 |
| Hard-coded config | Reliability | REQ-024 |
| Direct streaming | Simplicity | REQ-009 |

### 12. What We Don't Implement

- Retry logic
- Detailed error messages
- State persistence
- Custom queries
- Debug mode
- Performance metrics

---
**Focus**: Working demo over perfect code
**Target**: 50-100 lines maximum
**Priority**: Reliability for live demonstration