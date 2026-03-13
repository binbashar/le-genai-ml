# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This directory (`genai-agentcore-samples/`) is part of the [le-genai-ml](https://github.com/binbashar/le-genai-ml) monorepo and contains demonstration projects for AWS Bedrock AgentCore Runtime, showing how to deploy LangGraph-based agents to production serverless infrastructure. The project includes two independent demos with their own dependencies and deployments:

- **`01_runtime/`**: Basic translation agent demonstrating minimal deployment footprint
- **`02_async_streaming/`**: Advanced streaming and async task patterns for production workflows

## Architecture

### AgentCore Integration Pattern

All agents follow the decorator-based pattern:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def entrypoint_name(payload, context):
    # payload: Dict containing user input
    # context: AgentCore runtime metadata and utilities
    return {"result": "response"}
```

For streaming responses, use `@app.entrypoint` and yield intermediate updates.

For long-running background tasks (up to 8 hours), use `@app.async_task` decorator combined with `context.add_async_task()`.

### LangGraph Workflow Structure

Agents use LangGraph `StateGraph` with typed state dictionaries:
- Single-node workflows (01_runtime): Direct translation with `MessagesState`
- Multi-node workflows (02_async_streaming): Complex pipelines with custom `TypedDict` state extending `MessagesState`

Each agent creates a compiled graph via `StateGraph.compile()` that's invoked with state containing messages.

### Bedrock Model Configuration

All agents use AWS Bedrock models via `langchain_aws.ChatBedrock`:
- 01_runtime: `us.amazon.nova-micro-v1:0` (temperature 0.1)
- 02_async_streaming: `us.amazon.nova-micro-v1:0` (temperature 0.3)

**About Nova Micro Model ID:**
- `us.amazon.nova-micro-v1:0` is an **inference profile** (cross-region routing)
- Provides higher throughput by routing to us-east-1, us-west-2, or us-east-2
- Requires "Model Access" to be enabled in Bedrock console for first-time users
- Base model `amazon.nova-micro-v1:0` requires inference profile; cannot be invoked directly

Models are instantiated with `model_id` and `model_kwargs` parameters. Streaming is enabled via `streaming=True` parameter.

**Streaming Content Handling:**
Nova Micro returns content as list of objects: `[{'type': 'text', 'text': '...', 'index': 0}]`
Code extracts text from each block to ensure clean streaming output.

## Development Commands

### Prerequisites
- Python 3.13 (specified in `.python-version`)
- `uv` package manager (required for all commands)
- AWS credentials configured (`aws sts get-caller-identity`)
- Docker running (for deployment container builds)

### Common Workflows

#### Local Testing (Interactive)
```bash
# Test 01_runtime locally (interactive)
cd 01_runtime
uv run python translator_agent_local.py
# Press Enter for random example, or type text to translate

# Test 02_async_streaming locally (interactive)
cd 02_async_streaming
uv run python streaming_agent_local.py
# Press Enter for random query, or type your question
```

#### Install Dependencies
```bash
# Each directory has its own dependencies
cd 01_runtime
uv sync

cd 02_async_streaming
uv sync
```

#### Deploy to AWS AgentCore Runtime
```bash
cd 01_runtime  # or cd 02_async_streaming

# One-time configuration (creates .bedrock_agentcore.yaml)
uv run agentcore configure -e translator_agent.py

# Deploy (builds Docker image, pushes to ECR, creates Runtime)
uv run agentcore launch

# Invoke deployed agent
uv run agentcore invoke '{"prompt": "Hola!"}'
```

#### Update Existing Deployment
```bash
# Make code changes, then redeploy
uv run agentcore launch
# Creates new immutable version, updates DEFAULT endpoint
```

## Key Implementation Details

### Streaming Updates (02_async_streaming)

Yield intermediate messages with `type` field:
- `{"type": "thinking", "message": "..."}` - Progress updates
- `{"type": "stream_token", "token": "..."}` - LLM token streaming
- `{"type": "final", "result": "..."}` - Final response

Manual node invocation for step-by-step control:
```python
state = agent.nodes["node_name"].invoke(state)
```

### Async Task Management (02_async_streaming)

Three entrypoint patterns:
1. `start_report()`: Fire-and-forget, returns task_id immediately
2. `check_status()`: Polling endpoint for task progress
3. `start_report_with_polling()`: Streaming + blocking with progress yields

Task storage uses in-memory dict (`TASK_STORAGE`). In production, replace with DynamoDB or S3.

### Deployment Configuration

`.bedrock_agentcore.yaml` (auto-generated) contains:
- Entrypoint file path
- IAM execution role
- ECR repository settings
- Runtime configuration

`Dockerfile` pattern (all demos):
- Base: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`
- Install dependencies via `uv pip install .`
- AWS OpenTelemetry instrumentation included
- Runs as non-root user `bedrock_agentcore`
- Entrypoint: `opentelemetry-instrument python -m <module_name>`

## Git Commit Guidelines

When creating commits:
- Use clear, descriptive commit messages in English
- Do NOT include "Generated with Claude Code" watermarks
- Do NOT add "Co-Authored-By: Claude" attributions
- Keep commits clean and professional

## Important Conventions

### Versioning
AgentCore uses automatic immutable versioning:
- Version 1 created on first deployment
- New version on each `agentcore launch`
- DEFAULT endpoint always points to latest version
- Previous versions remain accessible for rollback

### Multiple Entrypoints
A single agent file can define multiple `@app.entrypoint` functions. Invoke specific entrypoint via:
```bash
uv run agentcore invoke --entrypoint entrypoint_name '{"key": "value"}'
```

### Project Structure
Each demo directory is self-contained:
- `*_agent.py`: AgentCore Runtime version (with decorator)
- `*_agent_local.py`: Interactive CLI version (same logic, no decorator, no AWS deployment needed)
- `pyproject.toml`: Dependencies
- `Dockerfile`: Container definition
- `.bedrock_agentcore.yaml`: Generated deployment config (after configure)

**Interactive Testing:**
All `*_agent_local.py` files support interactive mode. Run them directly and:
- Press **Enter** to select a random example
- Type your input to test with custom data

## AWS Permissions Required

For deployment:
- IAM role management (CreateRole, DeleteRole, GetRole, PutRolePolicy)
- CodeBuild access (StartBuild, BatchGetBuilds)
- ECR repository access (CreateRepository, GetAuthorizationToken)
- CloudWatch Logs access
- S3 access (for build artifacts)

For model access:
- `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions
- **No manual configuration needed** (October 2025): All serverless models are automatically enabled
- For legacy accounts only: enable Amazon Nova Micro in [Bedrock Console](https://console.aws.amazon.com/bedrock/home#/modelaccess)

Recommended: `BedrockAgentCoreFullAccess` managed policy for initial setup.
