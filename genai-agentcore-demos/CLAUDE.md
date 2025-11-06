# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production-ready financial advisory system demonstrating AWS Bedrock AgentCore with multi-agent orchestration. The system showcases:

- **Finance Personal Assistant**: Multi-agent orchestrator coordinating budget planning and investment analysis specialists
- **Interactive Streamlit UI**: Real-time streaming interface with OAuth2/Cognito authentication
- **Two Deployment Modes**: Production (full-featured) and Workshop (simplified learning version)

Each component is independently deployable with its own dependencies and deployment scripts.

## Quick Reference

| Task | Command | Location |
|------|---------|----------|
| **Deploy agent** | `./configure.sh && ./launch.sh` | `finance-personal-assistant/production/` |
| **Test all agents** | `./health.sh` | Project root |
| **Test one agent** | `./health.sh` | `finance-personal-assistant/production/` |
| **Run demo UI** | `./demo.sh` | Project root |
| **Reset memory** | `uv run reset_memory.py` | `finance-personal-assistant/production/` |
| **Complete cleanup** | `uv run cleanup.py` | `finance-personal-assistant/production/` |
| **View logs** | `aws logs tail /aws/bedrock-agentcore/runtimes/{id}-DEFAULT --follow` | Terminal |
| **Deploy guardrails** | `uv run deploy_guardrails.py` | `finance-personal-assistant/production/` |

## Repository Structure

```
genai-agentcore-demos/
├── finance-personal-assistant/
│   ├── production/              # Full production system
│   │   ├── main.py             # Orchestrator agent (AgentCore entrypoint)
│   │   ├── budget_agent.py     # Budget specialist
│   │   ├── financial_analysis_agent.py  # Investment specialist
│   │   ├── utils/              # Vision, PDF, CSV processing
│   │   └── cdk/                # Cognito + IAM infrastructure
│   │
│   └── workshop/               # Simplified workshop version
│       ├── lab1-*.ipynb        # Jupyter notebooks for learning
│       ├── lab2-*.ipynb        # Multi-agent workflows
│       └── lab3-*.ipynb        # AgentCore deployment
│
├── ui/                         # Streamlit demo interface
│   ├── app.py                  # Main Streamlit application
│   ├── config/agents.yaml      # Agent configuration (auto-synced)
│   └── utils/                  # Vision and document processing
│
├── libs/                       # Shared libraries
│   ├── cdk/                    # Reusable CDK constructs
│   │   ├── agent_execution_role.py
│   │   ├── agent_cognito.py
│   │   └── agent_app_client.py
│   │
│   └── python/                 # Runtime utilities
│       ├── agentcore_health.py  # Shared health check module
│       ├── auth_utils.py        # OAuth2/JWT authentication
│       └── ssm_utils.py         # SSM Parameter Store utilities
│
└── scripts/                    # Root-level utilities
    ├── health.sh               # Test all agents
    ├── demo.sh                 # Launch Streamlit UI
    └── reset_memory.sh         # Clear agent memory
```

## Common Development Commands

### Root-Level Scripts vs Agent-Specific Scripts

This project uses a two-tier script organization pattern:

**Root-level scripts** (orchestrators for all agents):
- `./health.sh` - Tests all agents in parallel, delegates to each agent's `health.sh`
- `./demo.sh` - Launches Streamlit UI with `AWS_PROFILE=binbash`
- `./scripts/reset_memory.sh` - Cross-agent memory reset utility
- `./scripts/health.py` - Multi-agent health check orchestrator

**Agent-specific scripts** (single agent operations):
- `finance-personal-assistant/production/health.sh` - Health check for finance assistant only
- `finance-personal-assistant/production/launch.sh` - Deploy finance assistant only
- `finance-personal-assistant/production/cleanup.py` - Cleanup finance assistant only
- `finance-personal-assistant/production/reset_memory.py` - Reset finance assistant memory only

**When to use root-level vs agent-specific:**
- Use **root-level** when testing/managing all deployed agents (e.g., `./health.sh` after deploying multiple agents)
- Use **agent-specific** when working on a single agent (e.g., `cd finance-personal-assistant/production && ./launch.sh`)

### Health Checks

All agents use a shared health check module with cascading fallback (AWS → Local):

```bash
# Check all agents (from project root)
./health.sh

# Check specific agent
cd finance-personal-assistant/production
./health.sh                    # Cascading fallback
./health.sh --aws              # Test deployed agent only
./health.sh --local            # Test local endpoint
./health.sh --timeout 120      # Custom timeout (default: 60s)
```

### Deploy Finance Assistant (Production)

```bash
cd finance-personal-assistant/production

# Option 1: With OAuth authentication (recommended)
cd cdk
./deploy.sh  # Creates Cognito, stores OAuth config in SSM
cd ..
./configure.sh  # Reads OAuth from SSM
./launch.sh     # Deploys to AgentCore Runtime, publishes ARN to SSM

# Option 2: IAM authentication only
./configure.sh  # Creates .bedrock_agentcore.yaml
./launch.sh     # Deploys to AgentCore Runtime

# Verify deployment
./health.sh
```

**What gets created:**
- Docker container with agent code
- ECR repository and image
- AgentCore Runtime with DEFAULT endpoint
- AgentCore Memory with 3 strategies (USER_PREFERENCE, SEMANTIC, SUMMARY)
- IAM execution role (auto-created by CLI)
- SSM parameter: `/agentcore/finance-personal-assistant/config` (agent ARN)
- Optional: Cognito User Pool + OAuth config

**Deployment flow (internal):**

When you run `./launch.sh`, this happens automatically:

1. `agentcore launch --auto-update-on-conflict` - Builds Docker, pushes to ECR, deploys to AgentCore Runtime
2. `libs/python/post_agent_deploy.py` - Reads agent ARN from `.bedrock_agentcore.yaml`, publishes to SSM
3. SSM parameter created/updated at `/agentcore/{agent_name}/config`

**Why this matters:** The Streamlit UI discovers agents by reading SSM parameters at runtime. No manual sync required! When you deploy an agent, it becomes immediately discoverable by the UI.

### Run Streamlit Demo

```bash
# From project root
./demo.sh
# Runs: export AWS_PROFILE=binbash && cd ui && ./demo.sh

# From ui directory
cd ui
./demo.sh
# Auto-discovers agents from SSM Parameter Store at runtime
```

**Streamlit features:**
- SSM-based agent discovery (no manual sync required)
- Real-time SSE streaming with tool execution feedback
- OAuth2/Cognito authentication support
- Vision analysis (receipts, invoices)
- Document upload (CSV/PDF)
- Session-based conversation history

### Local Testing

```bash
cd finance-personal-assistant/production

# Test individual agents
uv run python budget_agent.py
uv run python financial_analysis_agent.py

# Test vision analysis
uv run python test_vision.py
```

### Cleanup

```bash
cd finance-personal-assistant/production
uv run cleanup.py

# Options
uv run cleanup.py --dry-run     # Preview deletions
uv run cleanup.py --skip-iam    # Keep IAM roles
```

Removes:
- AgentCore Runtime and Memory instances
- ECR repositories and images
- CodeBuild projects, S3 artifacts
- SSM parameters
- IAM roles (unless --skip-iam)
- Local `.bedrock_agentcore.yaml`

### Reset Memory

```bash
cd finance-personal-assistant/production
uv run reset_memory.py

# Or from project root
./reset_memory.sh --agent finance-personal-assistant
```

Clears runtime-created LTM/STM while preserving configured memory infrastructure.

## Architecture Patterns

### Multi-Agent Orchestration

The production system uses an orchestrator pattern:

```python
# main.py - Orchestrator wraps specialists as tools
@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Budget planning and spending analysis"""
    return budget_agent.structured_output(output_model=FinancialReport, prompt=query)

@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Investment research and portfolio creation"""
    return financial_analysis_agent(query)

orchestrator_agent = Agent(
    model=model,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=SummarizingConversationManager(),
    session_manager=session_manager
)
```

**Routing:**
- Budget queries → `budget_agent_tool`
- Investment queries → `financial_analysis_agent_tool`
- Complex queries → Both agents (orchestrator synthesizes)

### Memory Management

Uses AgentCore Memory with three strategies (`memory_config.py`):

1. **USER_PREFERENCE**: User profile (name, goals, risk tolerance)
   - Namespace: `finance-assistant/user/{actorId}/preferences`
   - Top-K: 5, Relevance: 0.7

2. **SEMANTIC**: Financial facts (budgets, income, spending patterns)
   - Namespace: `finance-assistant/user/{actorId}/facts`
   - Top-K: 10, Relevance: 0.5

3. **SUMMARY**: Conversation summaries
   - Namespace: `finance-assistant/user/{actorId}/summaries/{sessionId}`
   - Top-K: 3, Relevance: 0.6

**Dual retrieval pattern:**
```python
# STM via session manager (automatic)
session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=AgentCoreMemoryConfig(...),
    retrieval_config=RETRIEVAL_CONFIG
)

# LTM via direct retrieval (manual injection into prompt)
from utils.memory_retrieval import retrieve_and_inject_memories
user_message = retrieve_and_inject_memories(
    memory_client=memory._client,
    memory_id=memory.memory_id,
    actor_id=actor_id,
    user_message=user_message
)
```

### Vision and Document Processing

Supports multiple document types with automatic detection:

**Images** (receipts, invoices):
```python
# Uses Amazon Nova Premier for vision analysis
vision_result = analyze_image(image_base64=image_base64)
user_message = inject_vision_context(user_message, vision_result)
```

**PDFs**:
```python
# Converts first page to image for vision analysis
from utils.pdf_processor import pdf_first_page_to_image
converted_image = pdf_first_page_to_image(document_base64)
```

**CSVs**:
```python
# Converts to text with formula injection prevention
from utils.csv_processor import csv_to_text
csv_text = csv_to_text(document_base64)
user_message = f"[CSV File Data]\n{csv_text}\n\nUser Query: {user_message}"
```

### Model Configuration

Shared `config.py` provides consistent Bedrock model management:

```python
from config import BedrockModelCatalog, get_bedrock_model

# For Strands agents
model = get_bedrock_model("strands", BedrockModelCatalog.CLAUDE_HAIKU_45)

# For LangGraph agents
llm = get_bedrock_model("langchain", BedrockModelCatalog.CLAUDE_SONNET_45, temperature=0.7)
```

**Available models:**
- Nova: `NOVA_MICRO`, `NOVA_LITE`, `NOVA_PRO`, `NOVA_PREMIER`
- Claude: `CLAUDE_HAIKU_45`, `CLAUDE_SONNET_37`, `CLAUDE_SONNET_45`

Model IDs use inference profiles (`us.amazon.nova-*`, `us.anthropic.claude-*`) for cross-region routing.

### Service Discovery via SSM

**Production architecture uses SSM Parameter Store for configuration:**

```bash
# Agent publishes ARN after deployment
./launch.sh  # Writes to /agentcore/finance-personal-assistant/config

# Streamlit discovers agents at runtime
# Uses libs/python/ssm_utils.py: get_all_agent_configs()
```

**SSM parameters:**
- `/agentcore/{agent_name}/config` - Unified config (ARN + OAuth)
- `/agentcore/{agent_name}/execution-role-arn` - IAM role (optional)

**No manual sync required!** Streamlit reads directly from SSM.

### Streamlit SSE Streaming

Real-time streaming with Server-Sent Events:

```python
def stream_agent_response(response_stream, tool_placeholder, timeout_seconds):
    """Generator yields tokens from SSE stream"""
    for line in response_stream.iter_lines():
        if line.startswith(b'data:'):
            event = json.loads(line[5:].decode('utf-8').strip())

            if event["type"] == "thinking":
                tool_placeholder.caption(f"🔧 {event['message']}")
            elif event["type"] == "stream_token":
                yield event["token"]
```

### Shared CDK Constructs

Reusable infrastructure patterns in `libs/cdk/`:

**AgentExecutionRole**:
- Comprehensive IAM permissions (Bedrock, Memory, ECR, CloudWatch, X-Ray)
- Optional Gateway permissions
- Auto-publishes ARN to SSM

**AgentCognito**:
- User Pool with MFA, password policies, email verification
- Standard security configuration

**AgentAppClient**:
- App Client for user authentication
- Token validity configuration (access: 60min, refresh: 30 days)

## Development Dependencies

**Production agent** (`finance-personal-assistant/production/pyproject.toml`):
- `strands-agents>=1.7.1` - Agent framework
- `langgraph>=1.0.1` - Graph workflows for financial analysis
- `bedrock-agentcore>=0.1.3` - AgentCore Runtime SDK
- `yfinance>=0.2.65` - Stock data
- `Pillow>=10.0.0` - Image processing
- `PyMuPDF>=1.24.0` - PDF processing

**Streamlit UI** (`ui/pyproject.toml`):
- `streamlit` - Web framework
- `boto3` - AWS SDK
- `pyyaml` - Config parsing
- `requests` - HTTP client
- `genai-agentcore-demos` - Parent package (shared utilities)

**Shared libraries** (`pyproject.toml`):
- `pip>=25.2`

## Important Conventions

### Deployment Artifacts

- `.bedrock_agentcore.yaml` - Generated by `agentcore configure/launch`, contains agent ARN
- Health checks read agent ARN from this file
- Structure: `agents.{agent_name}.bedrock_agentcore.agent_arn`

### SSM Configuration

**Unified parameter structure** (`/agentcore/{agent-name}/config`):
```json
{
  "arn": "arn:aws:bedrock-agentcore:...",
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://...",
      "allowedClients": ["client-id"]
    }
  }
}
```

### Session and Actor Management

**Actor ID extraction priority:**
1. `payload["actor_id"]` (works for both OAuth and IAM)
2. Request header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id`
3. Default: `"user"`

**Session ID requirements:**
- Minimum 33 characters (AgentCore Memory requirement)
- Auto-generated UUID if not provided or too short

### Health Check Architecture

All agents use `libs/python/agentcore_health.py` (~1000 lines) for consistency and reliability.

**Cascading fallback strategy:**
1. **AWS Mode**: Test deployed agent (reads ARN from `.bedrock_agentcore.yaml`)
2. **Local Mode**: Test local HTTP endpoint (port 8080) if AWS fails
3. **Success**: Report first working mode and exit

**Key features:**
- Dynamic region detection (respects `AWS_REGION`, falls back to boto3 config)
- Configurable timeout (default: 60s, adjustable via `--timeout SECONDS`)
- CLI flags: `--aws` (AWS only), `--local` (local only), `--timeout SECONDS`
- Exit code 0 for success, non-zero for errors
- Automatic retry logic with exponential backoff

**Creating health checks for new agents:**

1. Create minimal `health.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
from config import get_client

if __name__ == "__main__":
    config = AgentHealthConfig(
        agent_name="your_agent_name",
        agent_dir=str(Path(__file__).parent),
        default_prompt="Hello, are you operational?",
        aws_profile="binbash",
    )
    create_health_check_cli(config, get_client_func=get_client)
```

2. Create `health.sh`:
```bash
#!/bin/bash
uv run health.py "$@"
```

**Result:** Cascading fallback, dynamic region detection, configurable timeout.

## AWS Configuration

### Profile

Default: `AWS_PROFILE=binbash`

Verify: `AWS_PROFILE=binbash aws sts get-caller-identity`

### Required Permissions

- Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- AgentCore: `bedrock-agentcore:*` (or `BedrockAgentCoreFullAccess` managed policy)
- IAM: CreateRole, DeleteRole, GetRole, PutRolePolicy
- ECR: CreateRepository, GetAuthorizationToken
- CodeBuild: StartBuild, BatchGetBuilds
- CloudWatch Logs, S3
- **SSM Parameter Store**:
  - `ssm:GetParameter` - Read agent config
  - `ssm:PutParameter` - Write agent ARN/OAuth config
  - `ssm:GetParametersByPath` - Discover all agents
  - Scope to `/agentcore/*`

### Bedrock Model Access (October 2025 Update)

**No manual configuration needed.** As of October 2025, Amazon Bedrock automatically enables all serverless foundation models for every AWS account by default. The previous manual "Model Access" enablement process has been deprecated.

**What Changed:**
- All serverless foundation models (Nova, Claude, etc.) are automatically accessible without setup
- The Model Access page in the Bedrock Console has been deprecated
- The `PutFoundationModelEntitlement` IAM permission has been retired

**For Legacy Accounts Only:**

If you're using an older AWS account that still shows the Model Access page and requires manual enablement:
1. Visit: https://console.aws.amazon.com/bedrock/home#/modelaccess
2. Click "Modify model access"
3. Enable: Amazon Nova (all variants), Anthropic Claude 3.5/4.5
4. Access granted instantly

**Note:** Model access errors are now primarily IAM permission issues. Verify you have `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions.

**Reference:** [AWS Security Blog - Simplified Model Access](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)

### Region Configuration

Priority order:
1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable
3. boto3 session default (`~/.aws/config`)
4. Hardcoded default: `us-west-2`

## Typical Development Workflow

### Initial Setup

```bash
# Install dependencies
cd genai-agentcore-demos
uv sync

# Configure AWS
export AWS_PROFILE=your_profile
aws sso login --profile your_profile
cdk bootstrap
```

### Deploy with OAuth (Recommended)

```bash
cd finance-personal-assistant/production

# 1. Deploy Cognito infrastructure
cd cdk
./deploy.sh  # Creates users, stores OAuth in SSM
cd ..

# 2. Configure and launch agent
./configure.sh  # Reads OAuth from SSM
./launch.sh     # Deploys to AWS, publishes ARN to SSM

# 3. Verify
./health.sh
```

### Run Demo

```bash
# From project root
./demo.sh  # Auto-discovers agents from SSM
```

### Iterative Development

```bash
# Make code changes
cd finance-personal-assistant/production
# Edit main.py, budget_agent.py, etc.

# Test locally
uv run python budget_agent.py

# Redeploy
./launch.sh  # Creates new version, updates SSM

# Test
./health.sh
```

## Workshop Mode

The `finance-personal-assistant/workshop/` directory contains simplified Jupyter notebooks for learning:

- **Lab 1**: Develop a personal budget assistant with Strands
- **Lab 2**: Build multi-agent workflows with Strands
- **Lab 3**: Deploy agents on Amazon Bedrock AgentCore

Each lab is self-contained with step-by-step instructions.

## Monitoring

### CloudWatch Logs

```bash
# View agent logs (extract agent-id from .bedrock_agentcore.yaml)
grep agent_arn .bedrock_agentcore.yaml
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

### Health Endpoints

AgentCore Runtime provides:
- `/ping` - Basic health check
- `/invocations` - Main entrypoint

## Sample Queries

**Budget queries:**
- "I make $6000/month and want to start investing $500/month. Help me create a budget."
- "I spend too much on dining out ($800/month). How can I cut back?"

**Investment queries:**
- "Analyze Apple stock and tell me if it's a good investment."
- "Create a moderate risk portfolio for $10,000."

**Multi-agent queries:**
- "I make $5000/month and want to invest $1000. Help me budget and suggest a portfolio."

**Vision queries:**
- Upload receipt + "Help me track this expense in my budget."

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License**: Apache License 2.0 - See LICENSE file for details.

Workshop materials: https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US
