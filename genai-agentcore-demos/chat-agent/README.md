# Chat Agent

**Minimal LangGraph chat agent** built with AWS Bedrock AgentCore for experimentation and learning.

This is a lightweight conversational agent demonstrating core AgentCore patterns without the complexity of multi-agent orchestration.

## 📂 Repository Structure

```
chat-agent/
│
├── main.py                 🚀 AgentCore entrypoint with streaming
├── chat_agent_local.py     🧪 Local interactive testing
├── config.py               ⚙️  Model configuration (BedrockModelCatalog)
│
├── configure.sh            📋 Creates .bedrock_agentcore.yaml
├── launch.sh               🚀 Deploys to AWS + publishes to SSM
├── health.sh               ✅ Health check with cascading fallback
│
├── pyproject.toml          📦 Dependencies
└── README.md               📖 This file
```

---

## ✨ Features

✅ **LangGraph StateGraph** - Explicit state management with MessagesState
✅ **AgentCore Memory** - STM checkpointing via `langgraph-checkpoint-aws`
✅ **Async Streaming** - Token-by-token real-time response
✅ **Amazon Nova Lite** - Cost-effective model for experimentation
✅ **IAM Authentication** - Simple deployment (no OAuth setup required)
✅ **SSM Discovery** - Auto-discovery by Streamlit UI
✅ **Local Testing** - Interactive CLI for development

---

## 🚀 Quick Start

### Deploy to AWS

```bash
# Install dependencies
uv sync

# Configure agent (creates .bedrock_agentcore.yaml with STM memory)
./configure.sh

# Deploy to AWS (builds Docker, deploys to AgentCore, publishes to SSM)
./launch.sh

# Verify deployment
./health.sh
```

### Local Testing

```bash
# Interactive chat (no AWS deployment needed)
uv run python chat_agent_local.py

# Single message test
uv run python chat_agent_local.py "What is the capital of France?"

# Local HTTP endpoint (port 8080)
uv run agentcore launch --local
./health.sh --local
```

---

## 🏗️ Architecture

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | LangGraph | Explicit state management, checkpointer support |
| **Model** | Amazon Nova Lite | Lowest cost, fast for experimentation |
| **Memory** | AgentCore STM | Managed lifecycle via AgentCore CLI |
| **Auth** | IAM only | Simplest deployment path |
| **Streaming** | astream() | Token-by-token real-time response |

### LangGraph + AgentCore Memory Integration

Uses `langgraph-checkpoint-aws` package with `AgentCoreMemorySaver`:

```python
from langgraph_checkpoint_aws import AgentCoreMemorySaver

# Memory ID from environment (set by AgentCore Runtime)
memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
checkpointer = AgentCoreMemorySaver(memory_id, region_name=region)

# Create graph with checkpointer
graph = StateGraph(MessagesState).compile(checkpointer=checkpointer)

# Invoke with config (thread_id = session_id)
config = {"configurable": {"thread_id": session_id, "actor_id": actor_id}}
graph.invoke({"messages": [HumanMessage(content=user_message)]}, config)
```

### Streaming Pattern

Async `@app.entrypoint` with yield statements for SSE streaming:

```python
@app.entrypoint
async def chat(payload, context):
    yield {"type": "thinking", "message": "Generating response..."}

    async for chunk in llm.astream(messages):
        yield {"type": "stream_token", "token": token_text, "accumulated": full_response}

    yield {"type": "final", "result": full_response}
```

**Event types:**
- `thinking` - Progress updates (shown in UI)
- `stream_token` - Token-by-token streaming
- `final` - Complete response with metadata
- `error` - Error messages

---

## ⚙️ Model Configuration

Default model: **Amazon Nova Lite** (`us.amazon.nova-lite-v1:0`)

To change the model, edit `main.py`:

```python
llm = ChatBedrock(
    model_id="us.amazon.nova-lite-v1:0",  # Change to desired model
    model_kwargs={"temperature": 0.7},
)
```

Available models (see `config.py`):

| Model | ID | Description |
|-------|----|-------------|
| Nova Micro | `us.amazon.nova-micro-v1:0` | Ultra-fast, lowest cost |
| Nova Lite | `us.amazon.nova-lite-v1:0` | Fast, low-latency demos |
| Nova Pro | `us.amazon.nova-pro-v1:0` | Balanced for complex tasks |
| Nova Premier | `us.amazon.nova-premier-v1:0` | Premium for most complex tasks |
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-*` | Fast Claude responses |
| Claude Sonnet 3.7 | `us.anthropic.claude-3-7-sonnet-*` | Advanced reasoning |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-*` | Latest Claude reasoning |

---

## 📡 Payload Format

```json
{
    "prompt": "Your message here",
    "session_id": "optional-session-id",
    "actor_id": "optional-actor-id"
}
```

**Parameters:**
- `prompt` or `query` - User message (required)
- `session_id` - Session identifier for memory (auto-generated if not provided)
- `actor_id` - User identifier (default: "user")

---

## ✅ Health Checks

```bash
./health.sh                 # Cascading: AWS → Local
./health.sh --aws           # Test deployed agent only
./health.sh --local         # Test local HTTP endpoint
./health.sh --timeout 120   # Custom timeout (default: 60s)
```

Health checks use the shared module (`../libs/python/agentcore_health.py`) for consistency across all agents.

---

## 🔍 View Logs

```bash
# Extract agent-id from .bedrock_agentcore.yaml
grep agent_arn .bedrock_agentcore.yaml

# View real-time logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# View recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --since 10m
```

---

## 📋 Prerequisites

- **Python 3.13+**
- **AWS CLI v2** configured with your AWS profile
- **Docker** (for production deployments)
- **uv** package manager

### AWS Profile Configuration

```bash
# Configure AWS profile
aws configure --profile your-profile

# Set for this session
export AWS_PROFILE=your-profile

# Verify credentials
aws sts get-caller-identity
```

### Required Permissions

- Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- AgentCore: `bedrock-agentcore:*` (or `BedrockAgentCoreFullAccess`)
- SSM: `ssm:GetParameter`, `ssm:PutParameter` (for service discovery)

---

## 🔗 SSM Integration

After deployment, the agent ARN is published to SSM:

```bash
# Parameter path
/agentcore/chat_agent/config

# Content
{"arn": "arn:aws:bedrock-agentcore:us-west-2:..."}
```

The Streamlit UI (`../ui/`) reads this parameter to auto-discover the agent.

---

## 📦 Dependencies

Key dependencies from `pyproject.toml`:

```toml
dependencies = [
    "bedrock-agentcore>=0.1.3",
    "langgraph>=1.0.1",
    "langgraph-checkpoint-aws>=0.1.0",
    "langchain-aws>=1.0.0",
    "langchain-core>=1.0.0",
]
```

---

## 🧹 Cleanup

To remove the deployed agent and associated resources:

```bash
# Check deployment status
uv run agentcore status

# Delete agent (when cleanup script is available)
# uv run python cleanup.py
```

Or manually via AWS Console:
- AgentCore Runtime console
- ECR repository
- CloudWatch log groups

---

## 🚦 When to Use This Agent

### Use Chat Agent if you:
- Want to learn AgentCore + LangGraph basics
- Need a minimal agent for experimentation
- Are prototyping new features
- Want to understand the streaming pattern

### Use Finance Personal Assistant instead if you:
- Need multi-agent orchestration
- Require advanced memory strategies
- Need vision or document processing
- Are building a production application

---

## 📚 Resources

- **AgentCore Docs**: https://docs.aws.amazon.com/bedrock-agentcore/
- **AgentCore Toolkit**: https://aws.github.io/bedrock-agentcore-starter-toolkit/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **langgraph-checkpoint-aws**: https://pypi.org/project/langgraph-checkpoint-aws/
- **AWS Memory + LangGraph Integration**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html

---

## 📄 License & Attribution

Apache License 2.0 - See [LICENSE](../LICENSE) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**Original Source**: https://github.com/awslabs/amazon-bedrock-agentcore-samples

This implementation demonstrates basic AgentCore patterns with LangGraph for educational purposes and experimentation.
