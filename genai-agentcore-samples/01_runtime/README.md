# English Translator - AgentCore Runtime Demo

A basic translation agent demonstrating deployment to AWS Bedrock AgentCore Runtime using LangGraph and Bedrock LLMs.

## Project Overview

This demo includes two implementations:
- **`translator_agent_local.py`**: Standalone CLI version for local testing
- **`translator_agent.py`**: AgentCore Runtime version for AWS deployment

Both use the same LangGraph workflow and Bedrock model. The difference is the AgentCore decorator and runtime wrapper.

## Prerequisites

### 1. AWS CLI with Valid Credentials

[Configure your AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html) with valid credentials:

```bash
# Verify credentials
aws sts get-caller-identity
```

### 2. IAM Permissions

Your IAM user/role requires:

**For AgentCore Starter Toolkit:**
- IAM role management (`iam:CreateRole`, `iam:DeleteRole`, `iam:GetRole`, `iam:PutRolePolicy`)
- CodeBuild project access (`codebuild:StartBuild`, `codebuild:BatchGetBuilds`)
- ECR repository access (`ecr:CreateRepository`, `ecr:GetAuthorizationToken`)
- CloudWatch Logs access for monitoring
- S3 access for build artifacts

**For Bedrock Model Access:**
- `bedrock:InvokeModel` for Amazon Nova Micro (`us.amazon.nova-micro-v1:0`)
- [Enable model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) in the Bedrock console for your region (us-west-2)

**Recommended:** [Attach the `BedrockAgentCoreFullAccess` managed policy](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-attach-detach.html) to your IAM user for initial testing, then scope down to [custom policies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html) for production.

### 3. Package Manager: `uv`

[Install `uv`](https://docs.astral.sh/uv/getting-started/installation/), an extremely fast Python package manager:

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### 4. Docker

[Install Docker](https://docs.docker.com/get-docker/) for local container builds during deployment:

```bash
# Verify Docker is running
docker --version
```

## Installation

```bash
# Clone repository and navigate to project
cd english_translator

# Install all dependencies (including bedrock-agentcore-starter-toolkit)
uv sync
```

This installs:
- `bedrock-agentcore` (Runtime SDK)
- `bedrock-agentcore-starter-toolkit` (CLI for deployment)
- `langchain-aws`, `langgraph` (Agent framework)
- All required dependencies

## How AgentCore Integrates with Your Code

AgentCore uses a **decorator-based approach** that requires minimal changes to existing agent code:

### Local Agent (Before AgentCore)
```python
# translator_agent_local.py
def translate(payload):
    user_input = payload.get("prompt")
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    return response["messages"][-1].content
```

### AgentCore-Ready Agent (After)
```python
# translator_agent.py
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def translate(payload, context):
    user_input = payload.get("prompt")
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    return {"result": response["messages"][-1].content}
```

**What changed:**
1. Import `BedrockAgentCoreApp`
2. Add `@app.entrypoint` decorator to your invocation function
3. Add `context` parameter (provides runtime metadata)
4. Call `app.run()` at the end (handled automatically)

That's it. Your LangGraph workflow, model configuration, and business logic remain unchanged.

## Deployment Workflow

### 1. Local Testing

```bash
# Test locally before deploying
uv run python translator_agent_local.py '{"prompt": "Bonjour, comment �a va?"}'
```

### 2. Configure Agent

```bash
# One-time setup: configure entrypoint and AWS settings
uv run agentcore configure -e translator_agent.py
```

This creates `.bedrock_agentcore.yaml` with:
- Agent entrypoint
- IAM execution role (auto-created or specified)
- ECR repository settings
- Network and protocol configuration

### 3. Deploy to AgentCore Runtime

```bash
# Build container, push to ECR, create AgentCore Runtime
uv run agentcore launch
```

This:
1. Builds Docker image with your agent code
2. Pushes to Amazon ECR
3. Creates AgentCore Runtime with Version 1
4. Sets up `/invocations` and `/ping` HTTP endpoints
5. Returns agent ARN for invocation

### 4. Invoke Deployed Agent

```bash
# Invoke via starter toolkit
uv run agentcore invoke '{"prompt": "Hola, �c�mo est�s?"}'

# Response: {"result": "Hello, how are you?"}
```

## Versioning and Updates

### How Versioning Works

AgentCore Runtime uses **automatic, immutable versioning**:

- **Version 1** created automatically on first deployment
- **New versions** created on each update (code changes, config changes)
- **Immutable**: Each version is a complete snapshot and cannot be modified
- **DEFAULT endpoint**: Automatically points to the latest version

### Updating Your Agent

```bash
# Make code changes to translator_agent.py
# Then redeploy:
uv run agentcore launch
```

This creates a new version (e.g., Version 2) and updates the DEFAULT endpoint. Previous versions remain accessible for rollback if needed.

### Why This Matters for Production

- **Safe deployments**: Test new versions without affecting production traffic
- **Instant rollback**: Point endpoints to previous versions if issues occur
- **Audit trail**: Complete deployment history with immutable version records
- **Multi-environment**: Use different endpoints for dev/staging/prod pointing to different versions

This is the same versioning model used by production-grade services, ensuring your chatbot migrations maintain enterprise reliability standards.

[Learn more about AgentCore versioning →](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agent-runtime-versioning.html)

## Architecture

```
User Request
    ↓
AgentCore Runtime (HTTP Endpoint)
    ↓
LangGraph Workflow (Single-node translator)
    ↓
Amazon Bedrock Nova Micro
    ↓
English Translation Response
```

**Key Components:**
- **Runtime**: Serverless, auto-scaling HTTP service (port 8080)
- **LangGraph**: Single-node state graph with MessagesState
- **Bedrock Model**: `us.amazon.nova-micro-v1:0` with temperature 0.1
- **No state persistence**: Stateless, in-memory processing

## Next Steps: Expanding with AgentCore Services

This demo uses **AgentCore Runtime only**, but AgentCore provides additional services for production agents:

- **AgentCore Memory**: Persistent conversation history and retrieval-augmented generation (RAG)
- **AgentCore Gateway**: Transform APIs (OpenAPI, Smithy) and Lambda functions into agent tools without custom code
- **AgentCore Identity**: Inbound authentication (protect your agents) and outbound authentication (OAuth 2.0 for external APIs)
- **AgentCore Observability**: Trace agent executions, monitor performance, debug in production

These services integrate with the same `@app.entrypoint` pattern, allowing incremental adoption as your agent requirements grow.

## Support

For questions about AgentCore or deployment issues, refer to:
- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Starter Toolkit Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
