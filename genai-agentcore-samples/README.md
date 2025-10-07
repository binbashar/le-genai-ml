# AWS Bedrock AgentCore Runtime - Sample Implementations

Demonstrations of deploying LangGraph-based agents to AWS Bedrock AgentCore Runtime using serverless infrastructure.

## Overview

This collection showcases how to migrate existing agentic AI workflows to scalable infrastructure with minimal code changes. Each demo illustrates different AgentCore Runtime capabilities for deploying conversational AI agents.

## Demos

### 01_runtime - Basic Translation Agent
Minimal AgentCore Runtime deployment demonstrating the core decorator pattern and deployment workflow.

**Features:**
- Single-node LangGraph workflow
- Amazon Nova Micro LLM integration
- Stateless request/response pattern
- Interactive local testing
- Serverless container deployment

**Use Case:** Simple language translation service

[View detailed documentation →](./01_runtime/README.md)

### 02_async_streaming - Streaming & Parallel Execution
Advanced multi-node agent with real-time streaming updates and parallel LangGraph execution.

**Features:**
- Multi-node parallel execution (fan-out/fan-in pattern)
- Real-time streaming progress updates
- Token-by-token LLM streaming
- Custom state management with TypedDict

**Use Case:** Complex multi-step analysis with user feedback during processing

[View detailed documentation →](./02_async_streaming/README.md)

## Quick Start

### Prerequisites

- Python 3.13+ (specified in `.python-version`)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager
- AWS credentials configured
- Docker running (for deployments)
- Bedrock model access enabled for Amazon Nova Micro

### Local Testing

```bash
# Test translation agent
cd 01_runtime
uv run python translator_agent_local.py

# Test streaming agent
cd 02_async_streaming
uv run python streaming_agent_local.py
```

Both local versions support interactive mode:
- Press **Enter** for a random example
- Type your input for custom testing

### Deploy to AWS

```bash
# Navigate to demo directory
cd 01_runtime  # or 02_async_streaming

# Configure (one-time setup)
uv run agentcore configure -e translator_agent.py

# Deploy to AgentCore Runtime
uv run agentcore launch

# Invoke deployed agent
uv run agentcore invoke '{"prompt": "Hola!"}'
```

## Architecture Highlights

### AgentCore Integration Pattern

All demos use the same minimal decorator pattern:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def my_agent(payload, context):
    # Your LangGraph logic here
    return {"result": "response"}

if __name__ == "__main__":
    app.run()
```

**What AgentCore provides:**
- Automatic HTTP endpoint creation (`/invocations`, `/ping`)
- Session management
- Auto-scaling serverless compute
- Immutable versioning
- CloudWatch integration
- Container orchestration

### LangGraph Workflows

- **01_runtime**: Single-node `StateGraph` with `MessagesState`
- **02_async_streaming**: Multi-node parallel execution with custom state types

### Bedrock Models

All demos use Amazon Nova Micro (`us.amazon.nova-micro-v1:0`):
- Inference profile for cross-region routing
- Higher throughput via us-east-1, us-west-2, us-east-2
- Requires Bedrock Model Access enablement

## Project Structure

```
genai-agentcore-samples/
├── 01_runtime/              # Basic translation agent
│   ├── translator_agent.py           # AgentCore Runtime version
│   ├── translator_agent_local.py     # Local testing version
│   ├── Dockerfile
│   └── pyproject.toml
│
├── 02_async_streaming/      # Streaming agent with parallel execution
│   ├── streaming_agent.py            # AgentCore Runtime version
│   ├── streaming_agent_local.py      # Local testing version
│   ├── invoke_streaming.py           # Real-time streaming client
│   ├── Dockerfile
│   └── pyproject.toml
│
├── CLAUDE.md               # Developer guidance for Claude Code
└── README.md               # This file
```

Each demo is self-contained with its own dependencies and deployment configuration.

## Cost Considerations

AgentCore Runtime uses consumption-based pricing:
- **CPU**: $0.0895 per vCPU-hour (only during active processing)
- **Memory**: $0.00945 per GB-hour

**Important**: During streaming (I/O wait for LLM responses), CPU is NOT charged.

See [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/) for details.

## AWS Permissions

### Deployment Permissions
- IAM role management
- CodeBuild access
- ECR repository access
- CloudWatch Logs
- S3 (build artifacts)

### Runtime Permissions
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`

**Recommended:** Use `BedrockAgentCoreFullAccess` managed policy for initial setup.

**Enable Model Access:**
1. Go to [Bedrock Console - Model Access](https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess)
2. Click "Modify model access"
3. Enable "Amazon Nova Micro"
4. Access granted instantly (no approval needed)

## Production Features

### Versioning
- Immutable versions created on each deployment
- DEFAULT endpoint always points to latest
- Previous versions remain accessible for rollback

### Observability
- Automatic CloudWatch Logs integration
- OpenTelemetry instrumentation included
- Trace agent executions in production

### Multiple Entrypoints
Define multiple `@app.entrypoint` functions in a single file:

```bash
uv run agentcore invoke --entrypoint custom_handler '{"key": "value"}'
```

## Learning Path

**Recommended order:**

1. **Start with 01_runtime** - Understand the core deployment pattern
2. **Progress to 02_async_streaming** - Learn advanced streaming and parallel execution
3. **Explore invoke_streaming.py** - See production client integration patterns

## Resources

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Starter Toolkit Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Developer Guidance (CLAUDE.md)](./CLAUDE.md)

## Part of le-genai-ml

This project is part of the [binbashar/le-genai-ml](https://github.com/binbashar/le-genai-ml) monorepo, which contains various GenAI and ML implementations.

## License

See [LICENSE.txt](../LICENSE.txt) in the repository root.
