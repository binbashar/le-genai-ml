# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Market Trends Agent** - an intelligent financial analysis agent using Amazon Bedrock AgentCore that provides real-time market intelligence, stock analysis, and personalized investment recommendations. The agent combines LLM-powered analysis (Claude Sonnet 4) with live market data using LangGraph and maintains persistent memory of broker preferences across sessions.

## Core Architecture

### Agent Framework
- **LangGraph State Machine**: Uses `StateGraph` with `MessagesState` to build the conversational agent
- **Tool Binding Pattern**: Tools are bound to the LLM via `llm.bind_tools()`, with routing handled by `tools_condition`
- **Streaming Support**: LLM configured with `streaming=True` for real-time token-by-token response generation
- **Entry Point**: `market_trends_agent_runtime()` decorated with `@app.entrypoint` for AgentCore Runtime
- **Local Testing**: `market_trends_agent_local()` for development without deployment
- **OpenTelemetry Patch**: Auto-patches `bedrock_utils._decode_tool_use` to handle already-parsed dict inputs from Claude tool_use blocks

### Memory System (Multi-Strategy with Parallel Auto-Injection)

The agent uses Amazon Bedrock AgentCore Memory with **parallel automatic injection of both STM and LTM** for optimal performance and context.

**Memory Layers**:
- **STM (Short-Term Memory)**: Raw conversation events stored via `create_event()`, retrieved via `list_events()`
  - Scoped by `session_id` - each conversation gets a unique session
  - Automatically injected before each LLM invocation
- **LTM (Long-Term Memory)**: Extracted insights stored automatically by strategies
  - **USER_PREFERENCE Strategy**: Broker preferences, risk tolerance, investment styles (namespace: `market-trends/broker/{actorId}/preferences`)
  - **SEMANTIC Strategy**: Financial facts, market analysis, investment insights (namespace: `market-trends/broker/{actorId}/semantic`)
  - Automatically injected before each LLM invocation

**Parallel Automatic Context Injection (STM + LTM)**:
- `retrieve_context_parallel()` uses `asyncio.gather()` to retrieve **both** STM and LTM concurrently
- Latency = `max(stm_time, ltm_time)` instead of `stm_time + ltm_time` (~43% reduction)
- Context is **injected directly** into user messages as structured XML before each LLM invocation:
  ```xml
  <context>
    <conversation_history>Recent exchanges...</conversation_history>
    <broker_profile>Preferences, risk tolerance...</broker_profile>
  </context>
  ```
- Guarantees LLM always has complete context without manual tool calls

**Memory Discovery**:
- Uses `MemoryClient.create_or_get_memory()` built-in method for name-based discovery
- Automatically finds existing memory by name prefix or creates new instance
- No external coordination needed (removed SSM dependency)

**Session ID and Actor ID Pattern**:
- **Session ID**: Unique identifier for each conversation thread (e.g., UUID per chat session)
  - Used to scope STM retrieval - only retrieves history from the current conversation
  - Passed from `chat.py` → agent runtime → memory operations
  - Managed by `session_manager.py` for conversation tracking
- **Actor ID**: Identifies the user/entity across all sessions
  - Demo mode uses fixed `"demo-user"` actor ID
  - Production mode extracts actor ID from authenticated request context
  - Used for LTM namespacing and multi-user data isolation
- All memory operations use both `session_id` (for STM) and `actor_id` (for LTM) via closure scope

### Tool Categories

**Market Data Tools** (`tools/browser_tool.py`):
- `get_stock_data(symbol)`: Real-time stock prices via web scraping
- `search_news(query, news_source)`: Multi-source news (Bloomberg, Reuters, CNBC, WSJ, Financial Times, Dow Jones)
- Uses Playwright for browser automation with rate limiting

**Broker Profile Tools** (`tools/broker_card_tools.py`):
- `parse_broker_profile_from_message()`: Parse structured broker cards
- `generate_market_summary_for_broker()`: Tailored market analysis
- `get_broker_card_template()`: Provide profile format template
- `collect_broker_preferences_interactively()`: Guide preference collection

**Memory Tools** (`tools/memory_tools.py`):
- `retrieve_stm()`: Retrieve short-term memory (conversation history) for current session
- `retrieve_ltm()`: Retrieve long-term memory (broker profile) from all strategies
- `retrieve_context_parallel()`: **Auto-injection function** - Retrieves both STM and LTM in parallel using `asyncio.gather()`
- `compose_context()`: Formats context dict into XML structure for LLM injection
- `update_broker_financial_interests(info)`: **Tool** - Store new preferences for the authenticated user

## Chat Interfaces

### Interactive CLI Chat (`chat.py`)
Professional chat interface for deployed agents with session management:
- **Session Management**: Create, resume, and list conversation sessions
- **Streaming Responses**: Real-time token-by-token rendering with Rich Live display
- **Thinking Messages**: Shows tool execution progress inline (e.g., "Searching Bloomberg news...")
- **Markdown Rendering**: Beautiful formatted output with syntax highlighting
- **AWS Integration**: Connects to deployed AgentCore Runtime via boto3
- **Debug Mode**: Use `--debug` flag for detailed logging of tool calls, errors, and HTTP responses

```bash
# Start interactive chat (creates new session or resumes existing)
uv run python chat.py

# Enable debug mode to see tool execution details
uv run python chat.py --debug
```

**Features**:
- `StreamingResponseHandler`: Processes event-stream responses (SSE format)
- `MarkdownStreamRenderer`: Incremental markdown rendering with Rich Live
- Handles both streaming (`text/event-stream`) and legacy JSON responses
- Automatic AWS credential verification with helpful error messages

### Local Development Chat (`local_chat.py`)
Lightweight local testing without AWS deployment:
- **No Deployment Required**: Runs agent locally using your AWS credentials
- **Interactive Mode**: Choose from example queries or enter custom prompts
- **Quick Testing**: Ideal for rapid development iteration
- **Command-line Support**: Pass queries as arguments for scripting

```bash
# Interactive mode with example queries
uv run python local_chat.py

# Direct query execution
uv run python local_chat.py "Get Apple's current stock price"
```

**Use Cases**:
- Testing agent logic changes without redeploying
- Debugging tool integrations locally
- Rapid prototyping of new features
- Demo scenarios without cloud infrastructure

## Development Commands

### Setup & Installation
```bash
# Install dependencies
uv sync

# Install Playwright browsers (required for web scraping)
uv run playwright install
```

### Deployment
```bash
# Deploy agent to AWS
uv run python deploy.py

# Custom deployment options
uv run python deploy.py \
  --agent-name "my-market-agent" \
  --region "us-west-2" \
  --role-name "MyCustomRole"
```

### Testing
```bash
# Test deployed agent (non-streaming)
uv run python test_agent.py

# Test broker card functionality
uv run python test_broker_card.py

# Test local agent without deployment
uv run python test_local_agent.py

# Interactive local chat for development
uv run python local_chat.py

# Interactive chat with deployed agent (supports --debug)
uv run python chat.py
uv run python chat.py --debug  # Enable detailed logging
```

### Memory Management
```bash
# Reset memory (clears all data)
uv run python reset_memory.py

# Debug stored memories
uv run python debug_stored_memories.py

# Test automatic context injection
uv run python test_auto_context.py
```

### Cleanup
```bash
# Remove all AWS resources
uv run python cleanup.py

# Preview cleanup without deletion
uv run python cleanup.py --dry-run

# Keep IAM roles
uv run python cleanup.py --skip-iam
```

### Code Quality
```bash
# Format code
uv run black .

# Type checking
uv run mypy market_trends_agent.py

# Linting
uv run flake8 .

# Run tests
uv run pytest
```

## Key Implementation Details

### Agent Workflow (market_trends_agent.py)
1. User message enters via `market_trends_agent_runtime(payload, context)` with `session_id`
2. Actor ID is determined (hardcoded "demo-user" for demo mode)
3. Agent is created via `create_market_trends_agent(session_id, actor_id)`
4. Memory tools are created with `session_id` and `actor_id` closure scope for scoped memory operations
5. Message is wrapped in `HumanMessage` and passed to LangGraph agent
6. **PARALLEL AUTOMATIC INJECTION**:
   - `retrieve_context_parallel()` uses `asyncio.gather()` to fetch STM and LTM concurrently
   - `compose_context()` formats both into structured XML: `<context><conversation_history>...</conversation_history><broker_profile>...</broker_profile></context>`
   - Context injected into user message before LLM sees it
7. `chatbot()` node (async) processes message with optimized Claude Sonnet 4 system prompt, tool binding, and complete context
8. If tools needed (e.g., market data, preference updates), execution passes to `ToolNode` then back to `chatbot()`
9. LLM streams tokens back (if streaming enabled), or returns complete response
10. Conversations are automatically saved to AgentCore Memory with `session_id` and `actor_id`
11. Final response extracted from `messages[-1].content`

### Memory Creation Pattern (tools/memory_tools.py)
The `create_memory()` function uses the built-in `create_or_get_memory()` method:
1. Calls `client.create_or_get_memory(name, strategies, event_expiry_days)`
2. SDK tries to create memory with the given name
3. If "already exists" error, SDK automatically lists memories and finds matching one by name prefix
4. Returns memory instance (either newly created or existing)
5. No external coordination needed (SSM/files removed for simplicity)

### Deployment Configuration (.bedrock_agentcore.yaml)
- Platform: `linux/arm64` (AWS Graviton)
- Memory mode: `STM_ONLY` (Short-Term Memory)
- Event expiry: 30 days
- Network: `PUBLIC` mode with HTTP protocol
- Observability enabled via X-Ray and CloudWatch

## Important Patterns

### Claude Sonnet 4 Optimized System Prompt (market_trends_agent.py)
The system prompt follows Claude 4 agentic best practices:
- **XML Structure**: Uses `<memory_behavior>`, `<tool_usage>`, `<response_style>` tags for clear sectioning
- **Explicit Instructions**: "Use tools proactively" - action-oriented guidance for tool calling
- **Concise & Complete**: ~70% smaller than verbose prompts while maintaining all critical information
- **Token-Efficient**: Minimal prompt size reduces context usage and improves response quality

### Message Filtering (market_trends_agent.py)
The chatbot node implements sophisticated message filtering to:
- Remove empty messages while preserving tool_use/tool_result pairs
- Handle both string content and list-based content with tool blocks
- Prevent empty content from reaching the LLM
- Always prepend SystemMessage to filtered message list

### Streaming Response Handling (chat.py)
The chat interface uses a two-class architecture for streaming:

**StreamingResponseHandler**:
- Processes Server-Sent Events (SSE) from AgentCore Runtime
- Handles multiple event types: `thinking`, `stream_token`, `final`, `error`
- Manages Rich Live display lifecycle
- Optional debug mode for detailed event logging

**MarkdownStreamRenderer**:
- Incremental markdown rendering with Rich Live display
- Accumulates tokens and re-renders on each update
- Displays "thinking" messages inline (tool execution progress)
- Graceful fallback to plain text for incomplete markdown
- Automatic transition from thinking messages to response content

**Event Types**:
- `thinking`: Tool execution progress (e.g., "Searching Bloomberg news...")
- `stream_token`: Individual response tokens from Claude
- `final`: Complete response payload (fallback if no streaming)
- `error`: Error messages with optional debug details

### OpenTelemetry Patch (market_trends_agent.py)
Patches `bedrock_utils._decode_tool_use` to prevent JSON parsing errors:
- Claude returns tool_use blocks with dict inputs (already parsed)
- Original implementation tries to `json.loads()` the dict, causing errors
- Patched version checks if input is already a dict before parsing
- Applied automatically on agent initialization with error handling

### Container Deployment (deploy.py)
- Auto-detects `pyproject.toml` vs `requirements.txt` for dependency management
- Creates IAM role with comprehensive permissions (Bedrock, AgentCore, ECR, SSM, X-Ray, CloudWatch)
- Uses bedrock-agentcore-starter-toolkit's `Runtime` class
- Saves runtime ARN to `.agent_arn` file for testing

### Error Handling
- Memory operations include retry logic with exponential backoff
- Race condition protection during concurrent deployments
- Comprehensive logging at INFO level for debugging
- Graceful degradation when profiles don't exist

## Configuration Files

- **pyproject.toml**: Python 3.13+, uses uv for dependency management
- **.bedrock_agentcore.yaml**: Auto-generated by deployment, contains runtime ARNs and memory IDs
- **.agent_arn**: Stores deployed agent runtime ARN for testing
- **.memory_id**: Local cache of memory instance ID

## AWS Resources Created

- **AgentCore Runtime**: Serverless execution environment
- **AgentCore Memory**: Multi-strategy persistent storage
- **ECR Repository**: Container image storage
- **CodeBuild Project**: Container build pipeline
- **IAM Role**: Execution permissions (bedrock, agentcore, ecr, ssm, xray, logs)
- **SSM Parameter**: Memory ID coordination
- **CloudWatch Logs**: Runtime logs at `/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`

## Testing Notes

When testing locally or making changes:
1. The agent uses inference profile `us.anthropic.claude-sonnet-4-20250514-v1:0`
2. Temperature is set to 0.1 for consistent financial analysis
3. LLM streaming is enabled (`streaming=True`) for real-time token generation
4. Tools are invoked automatically by LangGraph's `tools_condition`
5. Memory operations are logged to help debug profile issues
6. Conversation history is saved automatically after each exchange
7. Use `chat.py --debug` to see detailed tool execution, error messages, and event streams
8. Use `local_chat.py` for rapid testing without AWS deployment
9. OpenTelemetry patch is automatically applied to prevent tool_use parsing errors
