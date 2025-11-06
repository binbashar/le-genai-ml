# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a monorepo (`le-genai-ml`) containing multiple GenAI and ML demonstrations and production implementations using AWS Bedrock, focusing on agentic AI workflows. The repository is organized into independent project directories, each with its own dependencies and deployment configurations.

## Repository Structure

### Primary Demo Projects

- **`genai-agentcore-demos/`**: Production-ready multi-agent financial advisory system
  - `finance-personal-assistant/`: Strands-based budget and financial planning agent with vision capabilities
  - `ui/`: Interactive Streamlit UI with SSM-based agent discovery
  - `libs/`: Reusable utilities (health checks, auth, CDK constructs, SSM utils)
  - `scripts/`: Common scripts for managing agents across the project
  - Root-level health check: `health.py` and `health.sh`

- **`genai-agentcore-samples/`**: Educational examples for AWS Bedrock AgentCore Runtime
  - `01_runtime/`: Basic translation agent (minimal deployment pattern)
  - `02_async_streaming/`: Advanced streaming and parallel execution

### Other Projects

- **`genai-bedrock-ai-agents-notebook/`**: Jupyter notebooks for agent workshops
- **`genai-llm-rag-bedrock-poc/`**: RAG chatbot proof of concept
- **`genai-langchain-samples/`**: LangChain structured output examples
- **`genai-vision-analyzer/`**: Vision analysis with Bedrock
- **`genai-product-spot-detector/`**: Product detection demo
- **`genai-agent-webscrapper/`**: Web scraping agent
- **`genai-speech2speech/`**: Speech-to-speech with Bedrock

Each directory is self-contained with its own `pyproject.toml`, dependencies, and deployment scripts.

## Development Environment

### Prerequisites

- **Python 3.13** (specified in `.python-version` files across projects)
- **`uv`** package manager (required for all development commands)
- **AWS credentials** configured with `AWS_PROFILE=binbash` (default profile for this repo)
- **Docker** (required for AgentCore deployments)
- **AWS Bedrock model access** enabled (see Model Access section below)

### AWS Profile Configuration

This repository uses `AWS_PROFILE=binbash` by default. Scripts like `ui/demo.sh` explicitly set this profile.

Verify credentials:
```bash
AWS_PROFILE=binbash aws sts get-caller-identity
```

## Common Development Commands

### AgentCore Demos (genai-agentcore-demos/)

The genai-agentcore-demos directory contains production agents with shared configuration.

#### Health Checks

All agents use a **shared health check module** (`libs/python/agentcore_health.py`) with cascading fallback.

```bash
# Check all agents (from genai-agentcore-demos/)
cd genai-agentcore-demos
./health.sh
# Runs: uv run health.py (tests finance-personal-assistant)

# Check individual agents
cd finance-personal-assistant
./health.sh     # Runs: uv run health.py

# Cascading mode (default): AWS → Local
./health.sh                    # Tries all modes until one succeeds

# Force specific mode
./health.sh --aws              # Test deployed agent only
./health.sh --local            # Test local HTTP endpoint (requires: agentcore launch --local)

# Adjust timeout
./health.sh --timeout 120      # Set response timeout (default: 60)
```

Health check features:
- **Cascading fallback**: Tries AWS → Local until one succeeds
- **Dynamic region detection**: Respects `AWS_REGION` env var, falls back to boto3 config
- **Configurable timeout**: Default 60s, adjustable via `--timeout`

#### Deploy Agents

Deploy using AWS Bedrock AgentCore CLI:

```bash
# Deploy finance personal assistant
cd genai-agentcore-demos/finance-personal-assistant

# 1. Configure (one-time, creates .bedrock_agentcore.yaml)
./configure.sh
# Or: uv run agentcore configure -e main.py

# 2. Deploy to AWS
./launch.sh
# Or: uv run agentcore launch

# 3. Verify deployment
./health.sh
```

**Optional: Add OAuth2 Authentication**

To enable OAuth2/JWT authentication with Cognito:

1. Deploy Cognito infrastructure:
```bash
cd finance-personal-assistant/cdk
./deploy.sh  # Creates Cognito User Pool + stores OAuth config in SSM
```

2. Configure agent with OAuth:
```bash
cd ..
./configure.sh  # Auto-detects OAuth config from SSM Parameter Store
./launch.sh
```

The CDK deployment automatically:
- Creates Cognito User Pool and Client
- Stores OAuth configuration in SSM at `/agentcore/{agent-name}/config` (unified parameter)
- `configure.sh` reads OAuth section from SSM and applies settings
- `launch.sh` publishes agent ARN to the same SSM parameter after deployment

**SSM Parameter Structure** (`/agentcore/{agent-name}/config`):
```json
{
  "arn": "arn:aws:bedrock-agentcore:...",  // Added by launch.sh
  "oauth": {                                 // Added by Cognito CDK (optional)
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.../.well-known/openid-configuration",
      "allowedClients": ["client-id-123"]
    }
  }
}
```

**Remove OAuth** (revert to IAM auth):
```bash
# Delete the entire config parameter (will be recreated without OAuth on next launch)
aws ssm delete-parameter --name "/agentcore/{agent-name}/config"
./configure.sh  # Falls back to IAM authentication
./launch.sh     # Recreates SSM parameter with ARN only
```

#### Service Discovery via SSM

**Production Architecture:** All services discover agent configurations through SSM Parameter Store (no file dependencies).

**Automatic Publishing:**
- `./launch.sh` automatically publishes agent ARN to SSM after successful deployment
- Streamlit reads agent configurations directly from SSM at runtime
- No manual sync required!

**SSM Parameters:**
- `/agentcore/{agent_name}/config` - Unified configuration (ARN + OAuth)
- `/agentcore/{agent_name}/execution-role-arn` - IAM role ARN (optional, for reuse)

**Discovery Flow:**
1. Cognito CDK writes OAuth config to SSM (if OAuth enabled)
2. `./launch.sh` deploys agent and writes ARN to same SSM parameter
3. Streamlit calls `ssm_utils.get_all_agent_configs()` to discover all agents
4. No file dependencies between services!

#### Run Streamlit Demo

```bash
# Option 1: From genai-agentcore-demos root (recommended)
cd genai-agentcore-demos
./demo.sh
# Runs: export AWS_PROFILE=binbash && cd ui && ./demo.sh

# Option 2: From ui directory
cd genai-agentcore-demos/ui
./demo.sh
# Runs: export AWS_PROFILE=binbash && uv run streamlit run app.py
```

Streamlit demo features:
- SSM-based agent discovery (auto-discovers deployed agents at runtime)
- Static YAML configuration (`config/agents.yaml`) for agent metadata (name, capabilities)
- Real-time SSE streaming from agents
- Tool execution feedback display
- OAuth2/Cognito authentication support (when configured)
- Session-based conversation history
- Editable scenario prompts

**Demo User Management:**
- Copy `.demo_users.json.example` to `.demo_users.json` to customize demo users
- Used by CDK post-deployment script to create Cognito users
- Format: JSON array with username, password, email, name fields

#### Local Testing

```bash
# Finance assistant - test individual components
cd genai-agentcore-demos/finance-personal-assistant
uv run python budget_agent.py
uv run python financial_analysis_agent.py
uv run python test_vision.py  # Test vision analysis with receipts/invoices
```

#### Cleanup

```bash
# Complete cleanup (from agent directory)
cd genai-agentcore-demos/finance-personal-assistant
uv run cleanup.py

# Options
uv run cleanup.py --dry-run     # Preview what will be deleted
uv run cleanup.py --skip-iam    # Keep IAM roles
uv run cleanup.py --region us-west-2

```

Agent cleanup removes:
- AgentCore Runtime instances
- AgentCore Memory instances
- ECR repositories and images
- CodeBuild projects
- S3 build artifacts
- SSM parameters (OAuth config, execution role ARN)
- IAM roles/policies (unless --skip-iam)
- Local `.bedrock_agentcore.yaml` file

#### Reset Memory

```bash
# Clear runtime-created memory (LTM/runtime STM) while preserving configured STM
cd genai-agentcore-demos/finance-personal-assistant
uv run reset_memory.py

# Or from project root
cd genai-agentcore-demos
./reset_memory.sh --agent finance-personal-assistant
```

**What gets deleted:**
- Runtime-created LTM memories (e.g., "FinancePersonalAssistantMemory-*")
- Any additional STM created at runtime (different from configured STM)

**What gets preserved:**
- Configured STM memory from `.bedrock_agentcore.yaml` (agent infrastructure)

### AgentCore Samples (genai-agentcore-samples/)

Educational samples demonstrating AgentCore Runtime deployment patterns.

#### Local Testing
```bash
# Test translation agent locally (interactive)
cd genai-agentcore-samples/01_runtime
uv run python translator_agent_local.py
# Press Enter for random example, or type text

# Test streaming agent locally (interactive)
cd genai-agentcore-samples/02_async_streaming
uv run python streaming_agent_local.py
```

#### Deploy to AWS
```bash
cd genai-agentcore-samples/01_runtime  # or 02_async_streaming

# One-time configuration (creates .bedrock_agentcore.yaml)
uv run agentcore configure -e translator_agent.py

# Deploy (builds Docker, pushes to ECR, creates Runtime)
uv run agentcore launch

# Invoke deployed agent
uv run agentcore invoke '{"prompt": "Hola!"}'

# Check deployment status
uv run agentcore status
```

### Other Projects

```bash
# Run product spot detector
cd genai-product-spot-detector
uv run streamlit run app.py

# Run vision analyzer
cd genai-vision-analyzer
uv run streamlit run app.py

# Run LangChain structured output tests
cd genai-langchain-samples/langchain-structured-output
uv run pytest test_structured_output.py
```

## Architecture Patterns

### Shared Model Configuration (genai-agentcore-demos)

The `finance-personal-assistant` uses a shared `config.py` pattern for Bedrock model management:

**Key components:**
- `BedrockModelCatalog`: Enum-based type-safe model registry
- `ModelConfig`: Immutable dataclass with factory methods
- `get_bedrock_model()`: One-liner factory supporting both Strands and LangChain frameworks

**Usage:**
```python
from config import BedrockModelCatalog, get_bedrock_model

# For Strands agents (finance-personal-assistant)
model = get_bedrock_model("strands", BedrockModelCatalog.NOVA_LITE)

# For LangChain agents (agentcore-samples)
llm = get_bedrock_model("langchain", BedrockModelCatalog.CLAUDE_SONNET_45, temperature=0.7)
```

**Available models:**
- Nova: `NOVA_MICRO`, `NOVA_LITE`, `NOVA_PRO`, `NOVA_PREMIER`
- Claude: `CLAUDE_HAIKU_45`, `CLAUDE_SONNET_37`, `CLAUDE_SONNET_45`

**Model IDs use inference profiles:**
- Nova models: `us.amazon.nova-*` (cross-region routing)
- Claude models: `us.anthropic.claude-*` (cross-region routing)
- Inference profiles route to us-east-1, us-west-2, or us-east-2 for higher throughput

### Framework Patterns

**Strands Agents** (finance-personal-assistant):
- Uses `strands.agents.Agent` and `strands.models.BedrockModel`
- Tool registration via `@agent.tool` decorator
- Memory management with `MemoryToolkit` (DynamoDB-backed)
- Optional guardrails via `guardrail_id`, `guardrail_version`, `guardrail_trace`

**LangGraph Agents** (agentcore-samples):
- Uses `langgraph.graph.StateGraph` with `MessagesState` or custom TypedDict
- Bedrock integration via `langchain_aws.ChatBedrockConverse`
- Multi-node workflows with parallel execution (fan-out/fan-in)
- Streaming support with token-by-token updates

**AgentCore Runtime Integration:**
- Decorator pattern: `@app.entrypoint` for REST endpoints
- Async tasks: `@app.async_task` for long-running operations (up to 8 hours)
- Automatic HTTP endpoints: `/invocations`, `/ping`
- Session management and auto-scaling included
- Immutable versioning on each deployment

### Document Processing Utilities

The finance assistant includes vision and document processing capabilities:

**CSV Processing** (`utils/csv_processor.py`):
- Base64-encoded CSV to text conversion
- CSV formula injection prevention (sanitizes =, +, -, @)
- Multi-encoding support (UTF-8, ISO-8859-1, CP1252)
- 5MB size limit with graceful error handling

**PDF Processing** (`utils/pdf_processor.py`):
- Base64-encoded PDF to text extraction
- PyMuPDF-based text extraction
- Metadata preservation (title, author, page count)
- 10MB size limit with error handling

**Vision Analysis** (`utils/vision_analyzer.py`):
- Amazon Nova Premier vision model integration
- Financial document analysis (receipts, invoices)
- Structured data extraction (merchant, date, total, items, category)
- Graceful fallback on errors

**Usage pattern:**
```python
# In AgentCore entrypoint
image_base64 = payload.get("image_base64")
if image_base64:
    vision_result = analyze_image(image_base64=image_base64)
    if vision_result["status"] == "success":
        # Inject vision context into user message
        user_message = inject_vision_context(vision_result, payload["prompt"])
```

### Memory Retrieval Utilities

**Shared module** (`utils/memory_retrieval.py`) provides reusable memory context retrieval:

```python
from utils.memory_retrieval import retrieve_memory_context

# Retrieve relevant context for user query
context = await retrieve_memory_context(
    query=user_message,
    actor_id=actor_id,
    session_id=session_id,
    memory_id=memory_id,
    region=region
)

# Returns formatted context string with:
# - User preferences (goals, constraints, risk tolerance)
# - Semantic facts (budget amounts, income, spending)
# - Session summaries (previous conversation outcomes)
```

**Benefits:**
- Parallel retrieval using `asyncio.gather()` for performance
- Multi-strategy retrieval (USER_PREFERENCE, SEMANTIC, SUMMARY)
- Formatted context ready for agent prompt injection
- Error handling with graceful fallback

### Shared CDK Constructs

Reusable CDK constructs in `genai-agentcore-demos/libs/cdk/`:

**AgentExecutionRole** (`agent_execution_role.py`):
- IAM execution role with comprehensive permissions
- ECR image access, CloudWatch logging, X-Ray tracing
- Bedrock model invocation, AgentCore Memory operations
- Optional Gateway permissions (`enable_gateway_permissions=True`)
- Automatic SSM publishing of role ARN

**AgentCognito** (`agent_cognito.py`):
- Cognito User Pool with standard configuration
- MFA, password policies, account recovery
- Email verification enabled
- Used by both agents and Gateway

**AgentAppClient** (`agent_app_client.py`):
- Cognito App Client for user authentication
- USER_PASSWORD_AUTH enabled
- ALLOW_REFRESH_TOKEN_AUTH enabled
- Custom token validity (access: 60min, ID: 60min, refresh: 30 days)

**Usage pattern:**
```python
from libs.cdk.agent_execution_role import AgentExecutionRole
from libs.cdk.agent_cognito import AgentCognito

# In CDK stack
cognito_stack = AgentCognito(self, "Cognito", agent_name="my-agent")
execution_role = AgentExecutionRole(
    self, "ExecutionRole",
    agent_name="my-agent",
    enable_gateway_permissions=True
)
```

### Multi-Agent Orchestration (finance-personal-assistant)

The finance-personal-assistant implements an orchestrator pattern that coordinates specialized agents:

```python
# Orchestrator delegates to specialized agents
@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Handle budgeting queries"""
    return budget_agent.structured_output(output_model=FinancialReport, prompt=query)

@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Handle investment queries"""
    return financial_analysis_agent(query)

orchestrator_agent = Agent(
    system_prompt="Route to budget_agent or financial_analysis_agent_tool based on query type",
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=SummarizingConversationManager(
        summary_ratio=0.3,
        preserve_recent_messages=5
    )
)
```

### Memory Management (finance-personal-assistant)

Uses AgentCore Memory with three-strategy pattern defined in `memory_config.py`:

1. **USER_PREFERENCE**: User's name, financial goals, preferences, risk tolerance
   - Namespace: `finance-assistant/user/{actorId}/preferences`
   - Top-K: 5, Relevance: 0.7

2. **SEMANTIC**: Budget amounts, spending patterns, income sources, constraints
   - Namespace: `finance-assistant/user/{actorId}/facts`
   - Top-K: 10, Relevance: 0.5

3. **SUMMARY**: Conversation summaries and session outcomes
   - Namespace: `finance-assistant/user/{actorId}/summaries/{sessionId}`
   - Top-K: 3, Relevance: 0.6

**Integration via session manager:**
```python
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=AgentCoreMemoryConfig(
        memory_id=memory.memory_id,
        session_id=session_id,
        actor_id=actor_id
    ),
    retrieval_config={...},  # From memory_config.py
    region_name=region
)

agent = Agent(..., session_manager=session_manager)
```

**Automatic context retrieval:**
- Memories retrieved in parallel using `asyncio.gather()`
- Injected into agent prompt before each invocation
- Session manager handles formatting and error handling

### Streamlit Demo Architecture (genai-agentcore-demos/ui)

Multi-agent demo with SSM-based agent discovery:

**Configuration:**
- **Static**: `config/agents.yaml` - Agent metadata (name, capabilities, display info)
- **Dynamic**: SSM Parameter Store - Agent ARNs and OAuth config (via `ssm_utils.py`)
- **Discovery**: Agents automatically discovered at runtime via `get_all_agent_configs()`

**Key features:**
- Real-time streaming from AgentCore Runtime via Server-Sent Events (SSE)
- Tool execution feedback via `type: thinking` events
- LaTeX escape handling for currency displays ($1,200 → \$1,200)
- Thinking process extraction and display in expanders
- OAuth2/Cognito authentication support (when configured)
- Session-based conversation history (saved to `sessions/` directory)
- Vision analysis support (upload receipts/invoices)
- Document upload (CSV/PDF processing)

**Streaming pattern:**
```python
# Generator yields tokens from SSE stream
def stream_agent_response(response_stream, tool_placeholder, timeout_seconds):
    for line in response_stream.iter_lines():
        if line.startswith(b'data:'):
            data_str = line[5:].decode('utf-8').strip()
            event = json.loads(data_str)

            if event["type"] == "thinking":
                # Display tool execution
                tool_placeholder.caption(f"🔧 {event['message']}")
            elif event["type"] == "stream_token":
                # Yield token for display
                yield event["token"]
```

## AWS Permissions and Model Access

### Required Permissions

**For development and deployment:**
- IAM role management (CreateRole, DeleteRole, GetRole, PutRolePolicy)
- CodeBuild access (StartBuild, BatchGetBuilds)
- ECR repository access (CreateRepository, GetAuthorizationToken)
- CloudWatch Logs access
- S3 access (build artifacts)
- Bedrock AgentCore Runtime (CreateAgentRuntime, InvokeAgentRuntime, etc.)
- **SSM Parameter Store** (for unified agent configuration):
  - `ssm:GetParameter` - Read agent config during `configure.sh` and Streamlit runtime
  - `ssm:PutParameter` - CDK writes OAuth config, `launch.sh` writes agent ARN
  - `ssm:GetParametersByPath` - Streamlit discovers all deployed agents
  - Scope to `/agentcore/*` path for least privilege

**For model invocation:**
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`

**Recommended:** Use `BedrockAgentCoreFullAccess` managed policy for initial setup.

### Bedrock Model Access (October 2025 Update)

**No manual configuration needed.** As of October 2025, Amazon Bedrock automatically enables all serverless foundation models for every AWS account by default. The previous manual "Model Access" enablement process has been deprecated.

**What Changed:**
- All serverless foundation models (Nova, Claude, etc.) are automatically accessible without setup
- The Model Access page in the Bedrock Console has been deprecated
- The `PutFoundationModelEntitlement` IAM permission has been retired
- IAM policies and Service Control Policies (SCPs) still control access if needed

**For Legacy Accounts Only:**

If you're using an older AWS account that still shows the Model Access page and requires manual enablement, follow the legacy process:

1. Go to: https://console.aws.amazon.com/bedrock/home#/modelaccess
2. Click "Modify model access"
3. Enable required models:
   - Amazon Nova (all variants: Micro, Lite, Pro, Premier)
   - Anthropic Claude 3.5/4.5 (Haiku, Sonnet)
4. Access is granted instantly (no approval needed)

**Note:** Model access errors are now primarily IAM permission issues rather than enablement issues.

**Reference:** [AWS Security Blog - Simplified Model Access in Amazon Bedrock](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)

## Deployment Artifacts

### AgentCore Demos and Samples
- `.bedrock_agentcore.yaml`: Auto-generated deployment config (after `agentcore configure`)
  - Contains entrypoint file path, IAM role, ECR repository, runtime settings
  - Includes agent ARN (referenced by health checks)
  - File structure: `agents.{agent_name}.bedrock_agentcore.agent_arn`
  - May include OAuth configuration if enabled
- Health checks read agent ARN from `.bedrock_agentcore.yaml`

### Dockerfiles
All AgentCore projects use similar Dockerfile pattern:
- Base: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`
- Dependencies: `uv pip install .`
- OpenTelemetry instrumentation included
- Non-root user: `bedrock_agentcore`
- Entrypoint: `opentelemetry-instrument python -m <module>`

## Code Quality

### Pre-commit Hooks
Configured in `.pre-commit-config.yaml`:
- **Black** formatter (Python 3.10 language version)

Run manually:
```bash
pre-commit run --all-files
```

### Testing
- Health checks: `health.py` scripts in each agent directory
- Unit tests: `test_*.py` files (minimal coverage currently)
- Interactive testing: `*_local.py` scripts for local development

## Important Conventions

### Dependency Management
- Each project directory has its own `pyproject.toml`
- Use `uv sync` to install dependencies in a project directory
- Virtual environments: `.venv/` directories (gitignored)

### Health Check Protocol

All agents use the **shared health check module** (`shared/agentcore_health.py`) for consistency and reusability.

**Creating health checks for new agents:**

1. Create minimal `health.py` in agent directory:
```python
#!/usr/bin/env python3
"""Health check for Your New Agent"""

import sys
from pathlib import Path

# Add parent directory to path for libs module
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
from config import get_client

if __name__ == "__main__":
    config = AgentHealthConfig(
        agent_name="your_new_agent",  # Must match name in .bedrock_agentcore.yaml
        agent_dir=str(Path(__file__).parent),
        default_prompt="Hello, are you operational?",
        aws_profile="binbash",
    )

    create_health_check_cli(config, get_client_func=get_client)
```

2. Create `health.sh` with argument forwarding:
```bash
#!/bin/bash
uv run health.py "$@"
```

**Result:** New agent gets health check capabilities:
- Cascading fallback (AWS → Local)
- Dynamic region detection
- Configurable timeout
- CLI flags: `--aws`, `--local`, `--timeout SECONDS`

**Requirements:**
- `health.py` script in agent directory
- Exit code 0 for healthy, non-zero for errors
- Shared module handles all complex logic

### IAM Roles

The `agentcore configure` CLI automatically creates IAM execution roles with:
- Bedrock model invocation permissions
- AgentCore Memory operations
- ECR image access
- CloudWatch logging
- X-Ray tracing
- OAuth2/token vault access (when configured)
- Proper AssumeRole conditions (SourceAccount, SourceArn)

Roles follow AWS best practices and are more comprehensive than custom implementations.

### Versioning (AgentCore)
- Version 1 created on first deployment
- New immutable version on each `agentcore launch`
- DEFAULT endpoint always points to latest version
- Previous versions remain accessible for rollback

### Region Configuration
Default region precedence order (defined in `config.py`):
1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable
3. boto3 session default (from `~/.aws/config`)
4. Hardcoded default: `us-west-2`

## Project-Specific Notes

### genai-agentcore-demos

**Production-ready financial advisory system** with modular components:

**Components:**
- **Finance Personal Assistant** (finance-personal-assistant): Multi-agent orchestrator for budget and investment advice
  - Orchestrator pattern coordinating budget and financial analysis specialists
  - AgentCore Memory with 3 strategies (USER_PREFERENCE, SEMANTIC, SUMMARY)
  - Vision analysis for receipts/invoices (Amazon Nova Premier)
  - Document processing (CSV/PDF extraction with security sanitization)
  - Optional Bedrock Guardrails for content filtering

- **Streamlit Demo** (ui): Interactive UI with dynamic agent discovery
  - SSM-based agent discovery (no manual sync required)
  - Real-time SSE streaming, tool execution feedback
  - Vision analysis, document upload, session history
  - OAuth2/Cognito authentication support

**Shared Infrastructure** (`libs/`):
- `python/agentcore_health.py`: Reusable health check module (~1000 lines, cascading fallback)
- `python/auth_utils.py`: OAuth2/JWT authentication utilities
- `python/ssm_utils.py`: SSM Parameter Store utilities for config discovery
- `cdk/`: Reusable CDK constructs (AgentExecutionRole, AgentCognito, AgentAppClient)

**Shared Patterns:**
- Root `pyproject.toml` manages shared utilities (importable as `genai-agentcore-demos`)
- Each component has its own `pyproject.toml` for component-specific deps
- Each agent has `config.py` for model management (BedrockModelCatalog pattern)
- Each agent has `memory_config.py` for memory strategy configuration

**Deployment Workflow:**
1. **Configure agent**: `cd finance-personal-assistant && ./configure.sh` (reads OAuth from SSM if available)
2. **Launch to AWS**: `./launch.sh` (builds Docker, deploys to AgentCore Runtime, publishes ARN to SSM)
3. **Run demo**: `cd ../ui && ./demo.sh` (auto-discovers agents from SSM)

**No manual sync required!** Streamlit auto-discovers agents from SSM Parameter Store at runtime.

### genai-agentcore-samples

**Educational examples** (not production):
- Each demo is fully self-contained
- Includes both AgentCore Runtime version (`*_agent.py`) and local testing version (`*_local.py`)
- Local versions support interactive mode: press Enter for random example, or type custom input

**Key differences from demos:**
- Simpler architecture (single-agent, fewer tools)
- Focused on demonstrating AgentCore deployment patterns
- Detailed documentation in per-demo READMEs

### genai-llm-rag-bedrock-poc

Legacy Streamlit chatbot with RAG:
- File: `app.py`
- Cases: `cases/code_generation.py`, `cases/translation_nlp.py`, `cases/extract_text_from_files.py`

### genai-vision-analyzer

Streamlit app for vision analysis:
- File: `app.py`
- Utils: `utils/bedrock_client.py`, `utils/image_processor.py`, `utils/auth.py`
- Setup script: `setup.sh`

## Monitoring

### CloudWatch Logs

```bash
# View agent logs (replace {agent-id} with actual ID from .bedrock_agentcore.yaml)
# Extract agent ID: grep agent_arn .bedrock_agentcore.yaml
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# View recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --since 1h
```

### Health Endpoints

AgentCore Runtime provides automatic health check endpoints:
- `/ping`: Basic health check
- `/invocations`: Main entrypoint

### Checking Deployment Status

```bash
# Check deployment status
cd genai-agentcore-demos/finance-personal-assistant
uv run agentcore status

# List all deployed agents
aws bedrock-agentcore list-agent-runtimes
```

## Recent Changes & Architecture Evolution

**Major updates** (as of current state):

1. **SSM-Based Service Discovery**: Agents publish configuration to SSM Parameter Store automatically. Streamlit discovers agents dynamically at runtime.

2. **Enhanced Vision Capabilities**: Finance assistant includes Amazon Nova Premier vision analysis for financial documents (receipts, invoices) with structured data extraction.

3. **Document Processing**: CSV and PDF processors with security sanitization (CSV formula injection prevention, size limits, multi-encoding support).

4. **Shared Libraries**: Reusable infrastructure patterns (health checks, auth, CDK constructs, SSM utils) consolidated in `libs/` directory.

## Resources

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Starter Toolkit Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/specification/2025-06-18/)
- [Workshop (multi-agent financial system)](https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US)
