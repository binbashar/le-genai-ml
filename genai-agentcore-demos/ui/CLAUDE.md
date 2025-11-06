# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive Streamlit web interface for AWS Bedrock AgentCore financial advisory system. Provides a unified chat interface for multiple AI agents with real-time streaming responses, OAuth2/Cognito authentication, and tool execution feedback.

This is the demo UI layer that coordinates with independently deployed backend agents.

## Development Commands

### Running the Application

```bash
# Standard run (auto-syncs agent config first)
./demo.sh
# Runs: cd .. && ./sync.sh && cd - && uv run streamlit run app.py

# Local development mode (connects to local Docker endpoints)
./demo.sh --local
# Sets AGENTCORE_LOCAL_MODE=1 before starting

# Direct run (no auto-sync)
uv run streamlit run app.py
```

**Note:** The `demo.sh` script automatically runs `../sync.sh` to ensure agent configuration is up-to-date before launching.

### Configuration Management

Agent configuration is **auto-generated** - do not edit manually:

```bash
# Sync agent ARNs from deployed agents to config/agents.yaml
cd ..
./sync.sh
# Reads: */.bedrock_agentcore.yaml
# Updates: ui/config/agents.yaml
```

The sync script automatically:
- Extracts agent ARNs from each agent's `.bedrock_agentcore.yaml`
- Detects OAuth vs IAM authentication mode
- Converts directory names to config keys (`market-trends-agent` → `market_trends_agent`)
- Preserves other agents not in sync list

**Configuration file:** `config/agents.yaml` (auto-synced, do not edit manually)

## Architecture

### Invocation Mode Priority

The application supports three invocation modes (checked in priority order):

1. **Local HTTP** (highest priority): `AGENTCORE_LOCAL_MODE=1` → `http://localhost:{port}/invocations`
   - Enabled via `./demo.sh --local`
   - Uses `invoke_local_endpoint()` with HTTP POST
   - Default port: 8080 (configurable via `local_port` in agents.yaml)

2. **AWS with OAuth/JWT** (medium priority): `oauth_config` present → HTTP with Bearer token
   - Uses `invoke_with_token()` with JWT authentication
   - Requires user login via Cognito
   - HTTP POST to AWS endpoint with `Authorization: Bearer {token}` header

3. **AWS with IAM** (lowest priority): No oauth_config → boto3 client with AWS credentials
   - Uses `boto3.client("bedrock-agentcore").invoke_agent_runtime()`
   - No user login required (uses AWS_PROFILE credentials)

**Agent configuration determines mode:**
```yaml
agents:
  market_trends_agent:
    arn: arn:aws:bedrock-agentcore:...
    oauth_config:           # If present → OAuth mode
      discovery_url: https://...
      client_id: abc123
    local_port: 8080        # Used when AGENTCORE_LOCAL_MODE=1
```

### Authentication Flow (OAuth Agents Only)

**Login gate pattern:**
```python
# 1. Check if agent requires OAuth
agent_info = agents_config["agents"][agent_type]
current_agent = st.session_state.get("agent_type")

# 2. Show login form if not authenticated
if agent_info.get("oauth_config") and current_agent != agent_type:
    # Display login form in main screen
    # On submit: authenticate() → store token in st.session_state
    # After login: st.rerun() to show chat interface
    st.stop()  # Block rest of app until logged in

# 3. Chat interface (authenticated or IAM agent)
# Use st.session_state["auth_token"] for OAuth agents
```

**Authentication is handled by shared module** (`libs/python/auth_utils.py`):
- `authenticate(auth_config, username, password)` → Returns token dict
- `invoke_with_token(agent_arn, token, prompt, session_id, region, timeout)` → Returns streaming response
- Supports standard OAuth2 ROPC flow with automatic Cognito fallback

### Session Management

Each agent maintains independent conversation history:

```python
# Session state keys (per agent)
messages_key = f"messages_{agent_type}"           # Chat history
session_id_key = f"session_id_{agent_type}"       # Backend session ID

# Session ID persistence
# - Stored in sessions/.{agent_type} file
# - Reused across Streamlit reruns
# - Minimum 33 characters (AWS requirement)
```

**Session files:** `sessions/.{agent_type}` (gitignored)

### Streaming Response Pattern

The application uses Server-Sent Events (SSE) for real-time streaming:

```python
def stream_agent_response(response_stream, tool_placeholder, timeout_seconds):
    """Generator that yields tokens from AgentCore SSE stream"""
    for line in response_stream.iter_lines(chunk_size=10):
        if line.startswith("data: "):
            event = json.loads(line[6:])  # Remove "data: " prefix

            if event.get("type") == "thinking":
                # Side effect: Update tool placeholder
                tool_placeholder.caption(f"🔧 {event['message']}")

            elif event.get("type") == "stream_token":
                # Yield token for st.write_stream()
                yield escape_latex_chars(event["token"])

            elif event.get("type") == "final":
                # Final response (non-streaming agents)
                yield event.get("result", "")
```

**Key features:**
- **LaTeX escape**: Prevents `$1,200` from rendering as math mode
- **Markdown header formatting**: Ensures headers start on new lines
- **Tool execution feedback**: Displays tool calls in real-time
- **Thinking process extraction**: Extracts `<thinking>` tags and shows in expander
- **Timeout handling**: 120-second default (configurable in agents.yaml)

### Health Check System

Optional health badges show agent connectivity status:

```python
ENABLE_HEALTH_BADGES = True  # Feature flag

# Health check flow
if ENABLE_HEALTH_BADGES:
    local_endpoint = get_agent_endpoint_url(agent_type)
    if local_endpoint:
        success, state, status_code = check_local_health(endpoint_url)  # GET /ping
    else:
        success, state, status_code = check_aws_health(agent_info, auth_config, token)  # POST /invocations

# Health states
# - "local": Green (connected to local Docker)
# - "live": Blue (connected to AWS)
# - "error": Red (connection failed)
```

**Notes:**
- AWS AgentCore Runtime does **not** expose `/ping` endpoint
- AWS health checks use minimal prompt via `/invocations` endpoint
- Local Docker containers expose `/ping` for health checks
- Health checks run once per agent on first selection
- OAuth agents only check health after authentication

## Dependencies

From `pyproject.toml`:

```toml
dependencies = [
    "streamlit",              # Web interface framework
    "boto3",                  # AWS SDK (IAM authentication mode)
    "pyyaml",                 # Config file parsing
    "watchdog>=6.0.0",        # File watching for auto-reload
    "requests",               # HTTP client (OAuth/local mode)
    "aiohttp",                # Async HTTP (used by shared modules)
    "genai-agentcore-demos",  # Parent package (shared utilities)
]
```

**Shared modules** (from parent package):
- `libs/python/auth_utils.py`: OAuth2 authentication, token management, agent invocation
- `libs/python/agentcore_health.py`: Health check utilities (not directly used by Streamlit)

## Configuration Files

### `config/agents.yaml` (Auto-Generated)

**DO NOT EDIT MANUALLY** - This file is auto-synced via `../sync.sh`:

```yaml
aws:
  region: us-west-2
  timeout_seconds: 120

agents:
  finance_personal_assistant:
    name: Finance Personal Assistant
    arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/finance_personal_assistant-ABC123
    oauth_config:                    # Optional - if present, requires OAuth
      discovery_url: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_ABC/.well-known/openid-configuration
      client_id: abc123xyz
      allowed_clients:
        - abc123xyz
    local_port: 8080                 # Optional - port for local mode

  market_trends_agent:
    name: Market Trends Agent
    arn: arn:aws:bedrock-agentcore:...
    # No oauth_config → IAM authentication
```

**Configuration is synced from:**
- `../finance-personal-assistant/.bedrock_agentcore.yaml`
- `../market-trends-agent/.bedrock_agentcore.yaml`

### `.env` File (Optional)

For automated health checks with OAuth agents:

```bash
# Copy from example
cp .env.example .env

# Contents:
AGENTCORE_HEALTH_USERNAME=broker_demo
AGENTCORE_HEALTH_PASSWORD=DemoPass123!
```

Used by health check system when testing OAuth-protected agents.

## UI Components

### Sidebar

- **AWS Connection Status**: Verifies `boto3` can reach AWS
- **Agent Selector**: Radio buttons with auth mode icons
  - 🔐 = OAuth/Cognito (requires login)
  - 🔑 = IAM (uses AWS credentials)
- **User Info** (OAuth agents): Shows username and logout button
- **Health Badge** (optional): Connection status indicator
- **Footer**: Event branding and technology attribution

### Main Screen

**For OAuth agents (not authenticated):**
- Agent title
- Login form (username, password, submit button)
- Error messages on failed authentication

**For authenticated/IAM agents:**
- Agent title
- Chat history (from session state)
- Chat input box
- Streaming responses with tool execution feedback
- Thinking process expander (if `<thinking>` tags present)

## Important Patterns

### LaTeX Escaping

Streamlit interprets `$` as LaTeX delimiters. Financial text must be escaped:

```python
def escape_latex_chars(text):
    """Prevents "$1,200 per month" from rendering as LaTeX"""
    return re.sub(r"\$", r"\\$", text)
```

### Markdown Header Formatting

Ensure markdown headers start on new lines:

```python
if re.match(r"^#{1,6}\s", token) and prev_char and prev_char != "\n":
    token = "\n" + token  # Add newline before header
```

### Thinking Process Extraction

Extract and display agent reasoning:

```python
# After streaming completes
thinking_pattern = r"<thinking>(.*?)</thinking>"
thinking_matches = re.findall(thinking_pattern, response_text, re.DOTALL)

if thinking_matches:
    with st.expander("💭 Thinking Process", expanded=False):
        st.text("\n\n".join(thinking_matches))

# Remove thinking tags from main response
cleaned_response = re.sub(thinking_pattern, "", response_text, flags=re.DOTALL).strip()
```

### Session State Structure

```python
# Per-agent keys (avoid conflicts when switching agents)
st.session_state[f"messages_{agent_type}"]     # List of message dicts
st.session_state[f"session_id_{agent_type}"]   # Backend session ID
st.session_state[f"health_status_{agent_type}"] # "local"/"live"/"error"
st.session_state[f"health_status_code_{agent_type}"] # HTTP status code

# Global authentication state (shared across agents)
st.session_state["auth_token"]    # JWT access token
st.session_state["username"]      # Logged-in username
st.session_state["agent_type"]    # Currently authenticated agent
```

## Development Workflow

### Testing with Local Agents

1. Start agent locally (from agent directory):
```bash
cd ../market-trends-agent
uv run agentcore launch --local
```

2. Run Streamlit in local mode:
```bash
./demo.sh --local
```

3. Verify endpoint URL in logs:
```
Using endpoint: http://localhost:8080
```

### Testing with AWS Agents

1. Deploy agent:
```bash
cd ../market-trends-agent
./launch.sh
```

2. Sync configuration:
```bash
cd ../streamlit-demo
cd .. && ./sync.sh && cd streamlit-demo
```

3. Run Streamlit:
```bash
./demo.sh  # Auto-syncs before starting
```

### Adding New Agents

1. Deploy agent with `agentcore launch`
2. Run sync script: `cd .. && ./sync.sh`
3. Restart Streamlit: `./demo.sh`

**No code changes needed** - configuration is auto-detected from deployed agents.

## Troubleshooting

### Connection Issues

| Issue | Solution |
|-------|----------|
| "AWS Not Connected" | Check `AWS_PROFILE` and run `aws sts get-caller-identity` |
| "Agent not found" | Run `../sync.sh` to update config/agents.yaml |
| "Authentication failed" | Verify Cognito user exists and password is correct |
| "Token expired" | Logout and login again (tokens expire after 1 hour) |
| Health check shows red | Agent may be cold-starting (wait 30s) or deployment failed |

### Configuration Issues

| Issue | Solution |
|-------|----------|
| Agent not in selector | Run `../sync.sh` - agent may not be deployed |
| Wrong auth mode | Check agent's `.bedrock_agentcore.yaml` for `authorizer_configuration` |
| Local mode not working | Verify `local_port` in agents.yaml matches Docker container port |

### Streaming Issues

| Issue | Solution |
|-------|----------|
| No streaming output | Check agent logs in CloudWatch |
| Timeout after 120s | Increase `timeout_seconds` in config/agents.yaml |
| LaTeX rendering errors | Verify `escape_latex_chars()` is applied to all tokens |
| Headers not formatted | Check header detection regex `^#{1,6}\s` |

## Feature Flags

Located at top of `app.py`:

```python
ENABLE_HEALTH_BADGES = True  # Show/hide connection status indicators
```

Set to `False` to disable health checks (improves page load time).

## Environment Variables

- **`AWS_PROFILE`**: AWS credentials profile (default: binbash)
- **`AWS_REGION`**: Override region from agents.yaml
- **`AGENTCORE_LOCAL_MODE`**: Enable local endpoint mode (set by `./demo.sh --local`)
- **`AGENTCORE_HEALTH_USERNAME`**: Username for OAuth health checks (from .env)
- **`AGENTCORE_HEALTH_PASSWORD`**: Password for OAuth health checks (from .env)

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License**: Apache License 2.0
