# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Most common commands:**
```bash
# Deploy to AWS (first time)
./configure.sh && ./launch.sh && ./health.sh

# Iterative development (code changes)
./launch.sh && ./health.sh

# Local testing (no deployment)
uv run agentcore launch --local
./health.sh --local

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

## Project Overview

The Chat Agent is a **minimal LangGraph agent** designed for experimentation and basic token generation. It demonstrates:

- **LangGraph StateGraph** with MessagesState for conversation tracking
- **AgentCoreMemorySaver** for short-term memory (STM) checkpointing
- **Async streaming** with token-by-token yields
- **Amazon Nova Lite** model for cost-effective experimentation
- **IAM authentication** (no OAuth/Cognito setup required)

**Parent project:** Part of `genai-agentcore-demos`, a monorepo containing multiple AgentCore demonstrations.

**Interactive UI:** The Streamlit demo (`../ui/`) auto-discovers this agent via SSM Parameter Store.

## Architecture

### Key Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | LangGraph | Explicit state management, checkpointer support |
| Model | Nova Lite | Lowest cost, fast for experimentation |
| Memory | AgentCore STM | Managed by AgentCore CLI, automatic lifecycle |
| Auth | IAM only | Simplest deployment path |
| Streaming | astream() | Token-by-token real-time response |

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

Uses async `@app.entrypoint` with yield statements:

```python
@app.entrypoint
async def chat(payload, context):
    yield {"type": "thinking", "message": "Generating response..."}

    async for chunk in llm.astream(messages):
        yield {"type": "stream_token", "token": token_text, "accumulated": full_response}

    yield {"type": "final", "result": full_response}
```

**Event types:**
- `thinking`: Progress updates shown in UI
- `stream_token`: Token-by-token streaming
- `final`: Complete response with metadata
- `error`: Error messages

## Repository Structure

```
chat-agent/
├── main.py          # AgentCore entrypoint with LangGraph + streaming
├── config.py        # Model/region configuration (BedrockModelCatalog)
├── pyproject.toml   # Dependencies (langgraph-checkpoint-aws)
├── health.py        # Health check wrapper (uses shared module)
├── health.sh        # Health check launcher
├── configure.sh     # Creates .bedrock_agentcore.yaml
├── launch.sh        # Deploys to AWS + publishes to SSM
└── CLAUDE.md        # This file
```

## Common Development Commands

### Deploy to AWS

```bash
# First time deployment
./configure.sh  # Creates .bedrock_agentcore.yaml with STM memory
./launch.sh     # Builds Docker, deploys to AgentCore, publishes to SSM

# Verify deployment
./health.sh
```

### Local Testing

```bash
# Install dependencies
uv sync

# Run locally (HTTP endpoint on port 8080)
uv run agentcore launch --local

# Test local endpoint
./health.sh --local
```

### Health Checks

```bash
./health.sh                 # Cascading: AWS → Local
./health.sh --aws           # Test deployed agent only
./health.sh --local         # Test local HTTP endpoint
./health.sh --timeout 120   # Custom timeout
```

### View Logs

```bash
# Extract agent-id from .bedrock_agentcore.yaml
grep agent_arn .bedrock_agentcore.yaml

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

## Configuration

### Memory Configuration

Memory is automatically created and managed by AgentCore CLI:

- Configure with: `--memory-type SHORT_TERM` (in configure.sh)
- Memory ID passed via: `AGENTCORE_MEMORY_ID` environment variable
- Checkpointer: `AgentCoreMemorySaver` from `langgraph-checkpoint-aws`

### Model Configuration

Default model: Amazon Nova Lite (`us.amazon.nova-lite-v1:0`)

To change the model, edit `main.py`:

```python
llm = ChatBedrock(
    model_id="us.amazon.nova-lite-v1:0",  # Change to desired model
    model_kwargs={"temperature": 0.7},
)
```

Available models (see `config.py`):
- Nova: `NOVA_MICRO`, `NOVA_LITE`, `NOVA_PRO`, `NOVA_PREMIER`
- Claude: `CLAUDE_HAIKU_45`, `CLAUDE_SONNET_37`, `CLAUDE_SONNET_45`

## Payload Format

```json
{
    "prompt": "Your message here",
    "session_id": "optional-session-id",
    "actor_id": "optional-actor-id"
}
```

**Parameters:**
- `prompt` or `query`: User message (required)
- `session_id`: Session identifier for memory (auto-generated if not provided)
- `actor_id`: User identifier (default: "user")

## SSM Integration

After deployment, agent ARN is published to SSM:

```bash
# Parameter path
/agentcore/chat_agent/config

# Content
{"arn": "arn:aws:bedrock-agentcore:us-west-2:..."}
```

The Streamlit UI (`../ui/`) reads this parameter to auto-discover the agent.

## Dependencies

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

## AWS Configuration

**Required permissions:**
- Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- AgentCore: `bedrock-agentcore:*` (or `BedrockAgentCoreFullAccess`)
- SSM: `ssm:GetParameter`, `ssm:PutParameter`

**Default profile:** `AWS_PROFILE=binbash`

Verify credentials:
```bash
AWS_PROFILE=binbash aws sts get-caller-identity
```

## Troubleshooting

### Health Check Fails

```bash
# Check deployment status
uv run agentcore status

# View recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --since 10m
```

### Memory Not Working

Memory requires the AgentCore-managed `AGENTCORE_MEMORY_ID` environment variable. Verify:
1. `configure.sh` includes `--memory-type SHORT_TERM`
2. Agent was deployed with `./launch.sh` (not manual deployment)

### Import Errors

Ensure parent path is in sys.path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

## Resources

- [AWS AgentCore Memory + LangGraph Integration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [langgraph-checkpoint-aws PyPI](https://pypi.org/project/langgraph-checkpoint-aws/)

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License:** Apache License 2.0
