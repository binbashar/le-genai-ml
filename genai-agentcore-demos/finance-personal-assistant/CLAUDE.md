# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Most common commands:**
```bash
# Production deployment
cd production && ./configure.sh && ./launch.sh && ./health.sh

# Local testing (no deployment)
cd production && uv run python budget_agent.py

# Workshop learning (open editor from genai-agentcore-demos/ for kernel detection)
cd ../../genai-agentcore-demos && cursor .  # Then navigate to workshop notebooks

# Run Streamlit UI
cd ../ui && ./demo.sh

# Cleanup everything
cd production && uv run python cleanup.py
```

## Project Overview

The Finance Personal Assistant demonstrates multi-agent financial advisory systems built with AWS Bedrock AgentCore and Strands Agents. It provides **two implementations**:

1. **Production** (`production/`): Enterprise-grade system with vision processing, guardrails, and OAuth2
2. **Workshop** (`workshop/`): Educational Jupyter notebooks for learning multi-agent concepts

**Parent project:** This directory is part of `genai-agentcore-demos`, a monorepo containing multiple AgentCore demonstrations. Shared libraries are located in `../libs/` (health checks, auth utilities, SSM utils, CDK constructs).

**Interactive UI:** The Streamlit demo (`../ui/`) auto-discovers this agent via SSM Parameter Store for real-time interaction with streaming responses.

### Which Directory Should You Use?

**Use `production/` when:**
- Building enterprise applications requiring vision, documents, OAuth, multi-strategy memory
- Deploying to production environments
- Need infrastructure-as-code (CDK stacks)
- Want scripted deployment workflows
- Need health checks, cleanup utilities, service discovery

**Use `workshop/` when:**
- Learning multi-agent concepts from scratch
- Running hands-on training sessions
- Need step-by-step Jupyter tutorials
- Have 1 hour to build and deploy a working agent
- Want to understand fundamentals before exploring production code

**Recommended approach:** Start with `workshop/` notebooks to learn core concepts (1 hour), then explore `production/` for enterprise implementation patterns.

### Core Architecture

Both implementations share the same multi-agent orchestration pattern:
- **Budget Agent**: Handles budgeting, spending analysis, savings recommendations (50/30/20 rule)
- **Financial Analysis Agent**: Manages investment research, stock analysis, portfolio creation
- **Orchestrator Agent**: Coordinates between specialists based on query type

## Repository Structure

```
finance-personal-assistant/         # This directory
├── production/                     # Full production implementation
│   ├── main.py                    # Orchestrator (AgentCore entrypoint)
│   ├── budget_agent.py            # Budget specialist with structured outputs
│   ├── financial_analysis_agent.py # Investment specialist
│   ├── config.py                  # Model configuration (BedrockModelCatalog)
│   ├── memory_config.py           # Memory strategies (3 strategies)
│   ├── utils/                     # Agent-specific utilities
│   │   ├── vision_analyzer.py    # Nova Premier vision
│   │   ├── csv_processor.py      # CSV to text
│   │   ├── pdf_processor.py      # PDF to image
│   │   ├── session_manager.py    # Session/actor extraction
│   │   ├── memory_retrieval.py   # LTM retrieval
│   │   └── guardrail*.py         # Content filtering
│   ├── cdk/                       # Infrastructure (Cognito + IAM)
│   ├── configure.sh               # Reads OAuth from SSM
│   ├── launch.sh                  # Deploys to AgentCore, publishes ARN to SSM
│   ├── health.sh                  # Cascading health checks (AWS → Local)
│   ├── cleanup.py                 # Complete resource cleanup
│   └── reset_memory.py            # Clear runtime memory
│
└── workshop/                      # Simplified learning materials
    ├── lab1-*.ipynb               # Budget agent with tools
    ├── lab2-*.ipynb               # Multi-agent orchestration
    ├── lab3-*.ipynb               # AgentCore deployment
    └── utils.py                   # Workshop helper utilities

# Parent project structure (genai-agentcore-demos/)
../                                # Parent directory
├── ui/                            # Streamlit demo (shared across all agents)
│   ├── app.py                    # Main Streamlit application
│   ├── config/agents.yaml        # Agent metadata (name, capabilities)
│   └── utils/                    # UI-specific utilities
│
├── libs/                          # Shared libraries (reusable across agents)
│   ├── python/
│   │   ├── agentcore_health.py  # Shared health check module (~1000 lines)
│   │   ├── auth_utils.py        # OAuth2/JWT authentication
│   │   └── ssm_utils.py         # SSM Parameter Store utilities
│   └── cdk/                      # Reusable CDK constructs
│       ├── agent_execution_role.py  # IAM execution role pattern
│       ├── agent_cognito.py         # Cognito User Pool pattern
│       └── agent_app_client.py      # Cognito App Client pattern
│
├── scripts/                       # Root-level orchestration scripts
│   ├── health.sh                 # Tests all agents in parallel
│   ├── demo.sh                   # Launches Streamlit UI
│   └── reset_memory.sh           # Cross-agent memory reset
│
└── finance-personal-assistant/   # This directory
```

## Common Development Commands

### Production Deployment

```bash
cd production/

# Option 1: With OAuth (recommended)
cd cdk && ./deploy.sh && cd ..  # Creates Cognito, stores OAuth in SSM
./configure.sh  # Reads OAuth from SSM
./launch.sh     # Deploys to AgentCore Runtime, publishes ARN to SSM

# Option 2: IAM only
./configure.sh  # Creates .bedrock_agentcore.yaml
./launch.sh     # Deploys to AgentCore Runtime

# Verify deployment
./health.sh                 # Cascading: AWS → Local
./health.sh --aws           # Test deployed agent only
./health.sh --timeout 120   # Custom timeout
```

**What gets created:**
- Docker container with agent code (auto-built)
- ECR repository and image
- AgentCore Runtime with DEFAULT endpoint
- AgentCore Memory with 3 strategies (USER_PREFERENCE, SEMANTIC, SUMMARY)
- IAM execution role (auto-created by CLI with comprehensive permissions)
- SSM parameter: `/agentcore/finance-personal-assistant/config` (agent ARN + OAuth)
- Optional: Cognito User Pool + OAuth configuration

### Local Testing (No Deployment)

```bash
cd production/

# Test individual agents
uv run python budget_agent.py
uv run python financial_analysis_agent.py

# Test vision analysis
uv run python test_vision.py
```

### Workshop (Learning Mode)

```bash
cd workshop/

# Start Jupyter
jupyter lab

# Open notebooks in order:
# 1. lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
# 2. lab2-build_multi_agent_workflows_with_strands.ipynb
# 3. lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb
```

**Workshop structure:**
- Each lab is self-contained with step-by-step instructions
- Takes ~1 hour to complete all three labs
- Builds progressively from single agent → multi-agent → deployment

### Guardrails (Production Only)

```bash
cd production/

# Deploy guardrail (idempotent)
uv run python deploy_guardrails.py

# Deploy with production version
uv run python deploy_guardrails.py --create-version

# Test guardrail
uv run python test_gambling_guardrail.py
```

**What gets created:**
- Bedrock Guardrail with gambling content filtering
- PII protection (email, phone, SSN redaction)
- SSM parameter: `/agentcore/finance-personal-assistant/guardrail-config`
- Automatic integration via `config.py` (no code changes needed)

### Cleanup

```bash
cd production/

# Preview deletions
uv run python cleanup.py --dry-run

# Complete cleanup
uv run python cleanup.py

# Keep IAM roles
uv run python cleanup.py --skip-iam
```

Removes: Runtime, Memory, ECR, CodeBuild, S3, SSM parameters, IAM roles, `.bedrock_agentcore.yaml`

### Reset Memory

```bash
cd production/
uv run python reset_memory.py
```

Clears runtime-created LTM/STM while preserving configured memory infrastructure.

### Streamlit UI Integration

The production agent integrates with the Streamlit demo located in `../ui/`:

```bash
# Run Streamlit UI (from any directory)
cd ../ui && ./demo.sh

# Or from project root
../../demo.sh
```

**How it works:**
1. Agent publishes ARN to SSM Parameter Store during `./launch.sh`
2. Streamlit reads SSM parameter `/agentcore/finance-personal-assistant/config` at runtime
3. UI auto-discovers agent (no manual sync required)
4. Real-time SSE streaming shows responses and tool execution

**UI features:**
- Session-based conversation history (saved to `../ui/sessions/`)
- Upload receipts/invoices for vision analysis
- Upload CSV/PDF documents for processing
- OAuth2 authentication (if configured)
- Editable scenario prompts
- Tool execution feedback display

## Key Architecture Patterns

### Multi-Agent Orchestration

The orchestrator wraps specialist agents as tools:

```python
# production/main.py
@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Generate structured financial reports"""
    return budget_agent.structured_output(output_model=FinancialReport, prompt=query)

@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Handle investment analysis"""
    return financial_analysis_agent(query)

orchestrator_agent = Agent(
    model=model,
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=SummarizingConversationManager(),
    session_manager=session_manager  # AgentCore Memory integration
)
```

**Routing logic:**
- Budget queries → `budget_agent_tool`
- Investment queries → `financial_analysis_agent_tool`
- Complex queries → Both agents (orchestrator synthesizes)

### Memory Configuration (Production)

Three strategies defined in `memory_config.py`:

1. **USER_PREFERENCE**: Name, goals, risk tolerance
   - Namespace: `finance-assistant/user/{actorId}/preferences`
   - Top-K: 5, Relevance: 0.7

2. **SEMANTIC**: Budget amounts, spending patterns
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

### Vision and Document Processing (Production)

Automatic format detection and processing:

**Images** (receipts, invoices):
```python
# Uses Amazon Nova Premier
vision_result = analyze_image(image_base64=image_base64)
user_message = inject_vision_context(user_message, vision_result)
```

**PDFs**:
```python
# Converts first page to image
from utils.pdf_processor import pdf_first_page_to_image
converted_image = pdf_first_page_to_image(document_base64)
```

**CSVs**:
```python
# Converts to text with formula injection prevention
from utils.csv_processor import csv_to_text
csv_text = csv_to_text(document_base64)
```

**Security features:**
- CSV formula injection prevention (sanitizes `=`, `+`, `-`, `@`)
- Size limits (CSV: 5MB, PDF: 10MB)
- Multi-encoding support (UTF-8, ISO-8859-1, CP1252)

### Using Shared Libraries (Production)

The production implementation uses shared libraries from the parent project:

**Health checks** (`../libs/python/agentcore_health.py`):
```python
# production/health.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
from config import get_client

config = AgentHealthConfig(
    agent_name="finance-personal-assistant",
    agent_dir=str(Path(__file__).parent),
    default_prompt="Hello, are you operational?",
    aws_profile="binbash",
)
create_health_check_cli(config, get_client_func=get_client)
```

**CDK constructs** (`../libs/cdk/`):
```python
# production/cdk/stacks/cognito_stack.py
from libs.cdk.agent_cognito import AgentCognito
from libs.cdk.agent_execution_role import AgentExecutionRole

cognito = AgentCognito(self, "Cognito", agent_name="finance-personal-assistant")
execution_role = AgentExecutionRole(
    self, "ExecutionRole",
    agent_name="finance-personal-assistant",
    enable_gateway_permissions=False
)
```

**SSM utilities** (used by Streamlit UI):
```python
# ../ui/app.py
from libs.python.ssm_utils import get_all_agent_configs

# Auto-discover all deployed agents
agent_configs = get_all_agent_configs()
# Returns: {"finance-personal-assistant": {"arn": "...", "oauth": {...}}}
```

### Model Configuration

Shared `config.py` provides consistent model management:

```python
from config import BedrockModelCatalog, get_bedrock_model

# For Strands agents
model = get_bedrock_model("strands", BedrockModelCatalog.CLAUDE_HAIKU_45)

# For LangGraph agents (financial_analysis_agent)
llm = get_bedrock_model("langchain", BedrockModelCatalog.CLAUDE_SONNET_45, temperature=0.7)

# Automatic guardrail discovery (production)
model = get_bedrock_model_with_guardrails(
    framework="strands",
    model=BedrockModelCatalog.CLAUDE_HAIKU_45,
)
```

**Available models:**
- Nova: `NOVA_MICRO`, `NOVA_LITE`, `NOVA_PRO`, `NOVA_PREMIER`
- Claude: `CLAUDE_HAIKU_45`, `CLAUDE_SONNET_37`, `CLAUDE_SONNET_45`

Model IDs use inference profiles for cross-region routing (us-east-1, us-west-2, us-east-2).

### Service Discovery (Production)

Agent configuration automatically published to SSM Parameter Store:

```bash
# Automatic on deployment
./launch.sh  # Publishes to /agentcore/finance-personal-assistant/config

# Streamlit UI reads directly from SSM (no manual sync)
# Uses ../libs/python/ssm_utils.py
```

**SSM parameter structure:**
```json
{
  "arn": "arn:aws:bedrock-agentcore:...",
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://...",
      "allowedClients": ["..."]
    }
  }
}
```

### Session and Actor Management (Production)

Protocol-based extraction pattern in `utils/session_manager.py`:

**Actor ID priority:**
1. `payload["actor_id"]` (preferred - works for both OAuth and IAM)
2. Request header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id`
3. Default: `"user"`

**Session ID requirements:**
- Minimum 33 characters (AgentCore Memory requirement)
- Auto-generated UUID if not provided or too short

### Structured Outputs

Budget agent uses Pydantic for type-safe outputs:

```python
# production/budget_agent.py
class BudgetCategory(BaseModel):
    name: str
    amount: float
    percentage: float

class FinancialReport(BaseModel):
    monthly_income: float
    budget_categories: List[BudgetCategory]
    recommendations: List[str]
    financial_health_score: int  # 1-10

# Generate structured response
structured_response = budget_agent.structured_output(
    output_model=FinancialReport,
    prompt=query
)
```

## Development Dependencies

**Production** (`production/pyproject.toml`):
- `strands-agents>=1.7.1` - Main agent framework
- `langgraph>=1.0.1` - Graph workflows (financial analysis agent)
- `bedrock-agentcore>=0.1.3` - AgentCore Runtime SDK
- `yfinance>=0.2.65` - Stock data retrieval
- `Pillow>=10.0.0` - Image processing
- `PyMuPDF>=1.24.0` - PDF to image conversion
- `playwright>=1.40.0` - Browser automation

**Workshop** (notebook dependencies):
- `strands-agents` - Core framework
- `boto3` - AWS SDK
- `matplotlib` - Charting

## Production vs Workshop Differences

| Feature | Workshop | Production |
|---------|----------|------------|
| **Purpose** | Learning & education | Enterprise deployment |
| **Duration** | 1 hour (3 labs) | Production-ready |
| **Memory** | STM only (auto-created) | Multi-strategy (3 strategies) |
| **Authentication** | Basic Cognito (manual) | CDK-managed OAuth2 |
| **Vision** | ❌ | ✅ Amazon Nova Premier |
| **Documents** | ❌ | ✅ CSV/PDF processing |
| **Deployment** | Manual (notebooks) | Scripted (configure.sh + launch.sh) |
| **Service Discovery** | Hardcoded ARNs | SSM Parameter Store |
| **Guardrails** | Basic (optional) | Production-grade with PII |
| **Tools** | Calculator, basic charts | yfinance, browser, memory utilities |
| **Infrastructure** | Manual setup | CDK stacks |

## Important Conventions

### Deployment Files

- `.bedrock_agentcore.yaml` - Generated by `agentcore configure/launch`
- Contains agent ARN, IAM role, ECR repository, runtime settings
- Health checks read from: `agents.{agent_name}.bedrock_agentcore.agent_arn`
- Never commit to git (contains deployment-specific config)

### Docker Pattern

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . .
RUN uv pip install .
RUN uv pip install aws-opentelemetry-distro>=0.10.1

RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

CMD ["opentelemetry-instrument", "python", "-m", "main"]
```

Key features: Non-root user, OpenTelemetry instrumentation, UV package manager

### IAM Roles

The `agentcore configure` CLI automatically creates IAM execution roles with:
- Bedrock model invocation permissions
- AgentCore Memory operations (Get, Put, List, Query)
- ECR image access
- CloudWatch logging
- X-Ray tracing
- OAuth2/token vault access (when configured)
- Proper AssumeRole conditions (SourceAccount, SourceArn)

Roles are more comprehensive than custom implementations and follow AWS best practices.

### Versioning

AgentCore Runtime uses immutable versioning:
- Version 1 created on first `agentcore launch`
- New version on each subsequent `agentcore launch`
- DEFAULT endpoint always points to latest version
- Previous versions remain for rollback

### Memory Lifecycle

- Created automatically if not exists (via `Memory._ensure_exists()`)
- Searches for existing memory by name prefix
- Reuses existing memory to preserve historical data
- Waits for memory to become ACTIVE before proceeding
- Event expiry: 90 days (configurable in `FINANCE_MEMORY_CONFIG`)

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
4. Access granted instantly (no approval needed)

**Note:** Model access errors are now primarily IAM permission issues. Verify you have `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions.

**Reference:** [AWS Security Blog - Simplified Model Access](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)

### Region Configuration

Priority order (defined in `config.py`):
1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable
3. boto3 session default (`~/.aws/config`)
4. Hardcoded default: `us-west-2`

## Typical Development Workflow

### Initial Setup (One-Time)

```bash
# Install dependencies
cd production/
uv sync

# Configure AWS
export AWS_PROFILE=your_profile
aws sso login --profile your_profile

# Optional: Set up demo users
cp ../../.demo_users.json.example ../../.demo_users.json
# Edit as needed
```

### Deploy Production Agent

```bash
cd production/

# Deploy infrastructure (optional - for OAuth)
cd cdk && ./deploy.sh && cd ..

# Configure and launch
./configure.sh  # Reads OAuth from SSM if exists
./launch.sh     # Deploys to AWS, publishes ARN to SSM

# Verify
./health.sh
```

### Iterative Development

```bash
cd production/

# Make code changes to main.py, budget_agent.py, etc.

# Test locally first
uv run python budget_agent.py
uv run python financial_analysis_agent.py

# Redeploy (creates new version)
./launch.sh

# Test deployed version
./health.sh
```

### Workshop Learning Path

```bash
cd workshop/

# Start Jupyter
jupyter lab

# Complete labs in order:
# Lab 1: Budget agent with tools (20 min)
# Lab 2: Multi-agent orchestration (20 min)
# Lab 3: AgentCore deployment (15 min)
```

## Monitoring

### CloudWatch Logs

```bash
# Extract agent-id from .bedrock_agentcore.yaml
cd production/
grep agent_arn .bedrock_agentcore.yaml

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

### Health Endpoints

AgentCore Runtime provides:
- `/ping` - Basic health check
- `/invocations` - Main entrypoint (POST with JSON payload)

### Observability Dashboard

Visit GenAI Observability Dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
```

## Sample Queries

### Budget Queries
- "I make $6000/month and want to start investing $500/month. Help me create a budget."
- "I spend too much on dining out ($800/month). How can I cut back and save more?"
- "Create a comprehensive financial report for someone earning $4000/month."

### Investment Queries
- "Analyze Apple stock and tell me if it's a good investment."
- "Create a moderate risk portfolio for $10,000."
- "Compare Tesla, Apple, and Google stocks over the last 6 months."

### Multi-Agent Queries
- "I make $5000/month and want to invest $1000. Help me budget and suggest an investment portfolio."
- "Analyze my $800 dining expenses against $5000 income, then recommend stocks to invest my savings."

### Vision Queries (Production Only)
- Upload receipt image + "Help me track this expense in my budget."
- Upload invoice image + "Add this to my monthly spending analysis."

### Document Queries (Production Only)
- Upload CSV transactions + "Analyze my spending patterns."
- Upload PDF statement + "Extract financial data from this document."

## Troubleshooting

### Health Check Fails

```bash
# Check deployment status
cd production/
uv run agentcore status

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --since 10m

# Verify memory is ACTIVE
aws bedrock-agentcore list-memories
```

### Memory Not Working

```bash
# Reset memory (clears runtime-created memories)
cd production/
uv run python reset_memory.py

# Verify memory configuration
grep memory_id .bedrock_agentcore.yaml
```

### OAuth Issues

```bash
# Verify OAuth config in SSM
aws ssm get-parameter --name "/agentcore/finance-personal-assistant/config"

# Remove OAuth (revert to IAM)
aws ssm delete-parameter --name "/agentcore/finance-personal-assistant/config"
./configure.sh  # Reconfigure without OAuth
```

## Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [AWS Bedrock AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Workshop Materials](https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US)

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License**: Apache License 2.0 - See LICENSE file for details.
