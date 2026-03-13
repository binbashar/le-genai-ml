# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Most common commands:**
```bash
# Deploy with OAuth (first time)
cd cdk && ./deploy.sh && cd .. && ./configure.sh && ./launch.sh && ./health.sh

# Deploy without OAuth
./configure.sh && ./launch.sh && ./health.sh

# Iterative development (code changes)
./launch.sh && ./health.sh

# Local testing (no deployment)
uv run python budget_agent.py

# Test vision analysis
uv run python test_vision.py

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# Reset memory
uv run python reset_memory.py

# Complete cleanup
uv run python cleanup.py
```

## Project Overview

This is the **production deployment** of the Finance Personal Assistant, a production-ready enhancement of the workshop materials located in `../workshop/`. It adds enterprise features for real-world deployment.

**Parent project:** This directory is part of `genai-agentcore-demos`, a monorepo containing multiple AgentCore demonstrations. Shared libraries are located in `../../libs/` (health checks, auth utilities, SSM utils, CDK constructs).

**Interactive UI:** The Streamlit demo (`../../ui/`) auto-discovers this agent via SSM Parameter Store for real-time interaction with streaming responses.

**Key differences from workshop:**
- **Vision analysis**: Process receipts/invoices with Amazon Nova Premier
- **Document processing**: CSV and PDF file handling with security sanitization
- **Guardrails**: Pre-check validation to prevent blocked content from entering conversation history
- **CDK infrastructure**: Automated Cognito/IAM deployment
- **Service discovery**: SSM Parameter Store integration for dynamic configuration
- **Enhanced memory**: LTM retrieval with parallel async patterns
- **Streaming**: Real-time SSE responses with tool execution feedback

**Architecture:**
- **Orchestrator** (`main.py`): Routes queries to specialized agents
- **Budget Agent** (`budget_agent.py`): 50/30/20 budgeting with structured Pydantic outputs
- **Financial Analysis Agent** (`financial_analysis_agent.py`): Investment research with yfinance

## Common Development Commands

### Local Testing (No Deployment)

```bash
# Test individual agents locally (interactive - they prompt for input)
uv run python budget_agent.py
uv run python financial_analysis_agent.py

# Test vision analysis with sample receipt
# Note: Requires ~/Pictures/receipt.png or modify RECEIPT_PATH in script
uv run python test_vision.py

# Test guardrails (after deployment)
uv run python test_gambling_guardrail.py
```

### Deploy to AWS

```bash
# Option 1: With OAuth authentication (recommended)
cd cdk
./deploy.sh  # Creates Cognito, stores OAuth config in SSM
cd ..
./configure.sh  # Reads OAuth from SSM, creates .bedrock_agentcore.yaml
./launch.sh     # Builds Docker, deploys to AgentCore, publishes ARN to SSM

# Option 2: IAM authentication only
./configure.sh  # Creates .bedrock_agentcore.yaml without OAuth
./launch.sh

# Verify deployment
./health.sh     # Cascading: AWS → Local
./health.sh --aws      # Test deployed agent only
./health.sh --local    # Test local HTTP endpoint
```

**Deployment flow:**

1. **CDK Infrastructure** (optional, for OAuth):
   - `cdk/deploy.sh` creates Cognito User Pool + App Client
   - Writes OAuth config to SSM: `/agentcore/finance-personal-assistant/config`
   - Creates demo users from `../../.demo_users.json` if present
   - Outputs saved to `cdk/outputs.json` (used by post-deploy script)

2. **Agent Configuration**:
   - `./configure.sh` reads OAuth from SSM (if exists)
   - Creates `.bedrock_agentcore.yaml` with:
     - Entrypoint: `main.py`
     - Request header allowlist: `Authorization,X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id`
     - Memory disabled (using custom memory config)
     - OAuth authorizer config (if found in SSM)

3. **Agent Deployment**:
   - `./launch.sh` runs `agentcore launch`:
     - Builds Docker image with UV package manager
     - Pushes to auto-created ECR repository
     - Creates/updates AgentCore Runtime
     - Creates DEFAULT endpoint (points to latest version)
   - Runs `post_agent_deploy.py`:
     - Publishes agent ARN to SSM (updates config)
     - Enables Streamlit UI auto-discovery

4. **Health Verification**:
   - `./health.sh` tests deployed agent
   - Uses shared `agentcore_health.py` module
   - Cascading fallback: AWS → Local

**What gets created:**
- Docker container with multi-agent system
- ECR repository and image
- AgentCore Runtime with DEFAULT endpoint
- AgentCore Memory (3 strategies: USER_PREFERENCE, SEMANTIC, SUMMARY)
- IAM execution role (auto-created by AgentCore CLI)
- `.bedrock_agentcore.yaml` with deployment metadata
- SSM parameter at `/agentcore/finance-personal-assistant/config`
- Optional: Cognito User Pool + OAuth config (if CDK deployed)

### Deploy Guardrails

```bash
# Deploy content filtering and PII protection
uv run python deploy_guardrails.py

# Deploy with production version (recommended)
uv run python deploy_guardrails.py --create-version

# Verify guardrail exists
uv run python deploy_guardrails.py --verify-only
```

**Guardrails block:**
- Gambling content (19+ terms)
- Sexual, violent, hateful content
- PII (email, phone, SSN) with automatic redaction
- Prompt attacks

### Iterative Development

```bash
# Make code changes to main.py, budget_agent.py, or financial_analysis_agent.py

# Redeploy (creates new immutable version)
./launch.sh

# Test deployed version
./health.sh
```

### Cleanup

```bash
# Preview what will be deleted
uv run python cleanup.py --dry-run

# Delete everything (Runtime, Memory, ECR, IAM, Guardrails, SSM)
uv run python cleanup.py

# Keep IAM roles
uv run python cleanup.py --skip-iam
```

### Reset Memory

```bash
# Clear runtime-created memories (preserves configured STM)
uv run python reset_memory.py
```

## Architecture Patterns

### Multi-Agent Orchestration

The orchestrator wraps specialists as tools and routes queries based on content:

```python
@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Generate structured financial reports"""
    return budget_agent.structured_output(output_model=FinancialReport, prompt=query)

@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Handle investment queries"""
    return financial_analysis_agent(query)

orchestrator_agent = Agent(
    model=model,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=SummarizingConversationManager(),
    session_manager=session_manager  # AgentCore Memory
)
```

**Routing:**
- Budget queries → `budget_agent_tool`
- Investment queries → `financial_analysis_agent_tool`
- Complex queries → Both agents (orchestrator synthesizes)

### Memory Management (Dual Pattern)

Uses **both** Session Manager (STM) and Direct Retrieval (LTM):

**Pattern 1: Session Manager (STM)**
```python
session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=AgentCoreMemoryConfig(
        memory_id=memory.memory_id,
        session_id=session_id,
        actor_id=actor_id
    ),
    retrieval_config=RETRIEVAL_CONFIG,
    region_name=region
)
```

**Pattern 2: Direct Retrieval (LTM)**
```python
from utils.memory_retrieval import retrieve_and_inject_memories

user_message = retrieve_and_inject_memories(
    memory_client=memory._client,
    memory_id=memory.memory_id,
    actor_id=actor_id,
    user_message=user_message,
    namespaces={
        "finance-assistant/user/{actorId}/preferences": 5,
        "finance-assistant/user/{actorId}/facts": 10,
    }
)
```

**Memory strategies** (defined in `memory_config.py`):
1. **USER_PREFERENCE**: Name, goals, risk tolerance (Top-K: 5, Relevance: 0.7)
2. **SEMANTIC**: Budget amounts, spending patterns (Top-K: 10, Relevance: 0.5)
3. **SUMMARY**: Conversation summaries (Top-K: 3, Relevance: 0.6)

### Vision and Document Processing

Automatic format detection in `main.py` entrypoint:

**Vision (images):**
```python
image_base64 = payload.get("image_base64")
if image_base64:
    vision_result = analyze_image(image_base64=image_base64)
    user_message = inject_vision_context(user_message, vision_result)
```

**PDF (converted to image):**
```python
if filename.endswith(".pdf"):
    from utils.pdf_processor import pdf_first_page_to_image
    converted_image = pdf_first_page_to_image(document_base64)
    payload["image_base64"] = converted_image  # Process with vision
```

**CSV (converted to text):**
```python
if filename.endswith(".csv"):
    from utils.csv_processor import csv_to_text
    csv_text = csv_to_text(document_base64)
    user_message = f"[CSV File Data]\n{csv_text}\n\nUser Query: {user_message}"
```

**Vision model:**
- Amazon Nova Premier (`us.amazon.nova-premier-v1:0`)
- Temperature: 0.1 (deterministic extraction)
- Max tokens: 4096

**CSV security:**
- Formula injection prevention (sanitizes `=`, `+`, `-`, `@`)
- Multi-encoding support (UTF-8, ISO-8859-1, CP1252)
- 5MB size limit

**PDF processing:**
- PyMuPDF-based first page extraction
- Converts to PNG for vision
- 10MB size limit

### Guardrail Pre-Check Pattern

Validates user input BEFORE agent processing to prevent conversation history contamination:

```python
# main.py - Pre-check in entrypoint (before agent invocation)
guardrail_config = get_guardrail_config()
if guardrail_config:
    from utils.guardrail_sanitize import apply_guardrail_text

    pre_check_result = apply_guardrail_text(
        text=user_message,
        guardrail_id=guardrail_config.get("guardrail_id"),
        guardrail_version=guardrail_config.get("guardrail_version"),
        source="INPUT",
    )

    if not pre_check_result["is_safe"]:
        # Return intervention message WITHOUT invoking agent
        yield {"type": "final", "result": "I can't assist with that request."}
        return
```

**Key insight:** Pre-check prevents blocked content from entering conversation history, avoiding re-triggering on subsequent turns.

### Model Configuration

Centralized in `config.py` with enum-based type safety:

```python
from config import BedrockModelCatalog, get_bedrock_model

# Strands agents
model = get_bedrock_model("strands", BedrockModelCatalog.CLAUDE_SONNET_45)

# LangGraph agents
llm = get_bedrock_model("langchain", BedrockModelCatalog.CLAUDE_SONNET_45, temperature=0.7)
```

**Available models:**
- Nova: `NOVA_MICRO`, `NOVA_LITE`, `NOVA_PRO`, `NOVA_PREMIER`
- Claude: `CLAUDE_HAIKU_45`, `CLAUDE_SONNET_37`, `CLAUDE_SONNET_45`

**Model IDs use inference profiles** (`us.amazon.*`, `us.anthropic.*`) for cross-region routing.

**Automatic guardrail discovery:**
```python
def get_guardrail_config() -> dict[str, str] | None:
    # Try SSM first (service discovery pattern)
    ssm.get_parameter("/agentcore/finance-personal-assistant/guardrail-config")
    # Fallback to direct API lookup
    get_gambling_guardrail_id()
```

### Session and Actor Management

Protocol-based pattern in `utils/session_manager.py`:

```python
from utils.session_manager import extract_session_context

@app.entrypoint
async def invoke(payload, context):
    session_ctx = extract_session_context(context, payload)
    session_id = session_ctx.session_id  # Auto-generated if not provided
    actor_id = session_ctx.actor_id      # From payload or header
```

**Actor ID extraction priority:**
1. `payload["actor_id"]` (most reliable - works for OAuth and IAM)
2. Request header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id`
3. Default: `"user"`

**Session ID validation:**
- Minimum 33 characters required by AgentCore Memory
- Auto-generated UUID if too short or missing

## Project Structure

```
production/
├── main.py                      # Orchestrator entrypoint (AgentCore)
├── budget_agent.py              # Budget specialist (Pydantic outputs)
├── financial_analysis_agent.py  # Investment specialist (yfinance)
├── config.py                    # Model configuration + guardrail discovery
├── memory_config.py             # Memory strategies (3-strategy pattern)
├── test_vision.py               # Vision testing script
├── deploy_guardrails.py         # Guardrail deployment script
├── cleanup.py                   # Complete cleanup (Runtime, Memory, ECR, IAM)
├── reset_memory.py              # Reset runtime-created memories
│
├── utils/
│   ├── vision_analyzer.py       # Nova Premier vision analysis
│   ├── vision_context.py        # Vision context injection
│   ├── csv_processor.py         # CSV to text (formula injection prevention)
│   ├── pdf_processor.py         # PDF to image (PyMuPDF)
│   ├── session_manager.py       # Session/actor extraction (Protocol-based)
│   ├── memory_retrieval.py      # LTM retrieval (parallel async)
│   ├── guardrail.py             # Guardrail management utilities
│   └── guardrail_sanitize.py    # Pre-check validation (ApplyGuardrail API)
│
├── cdk/                         # CDK infrastructure (Cognito + IAM)
│   ├── app.py                   # CDK app (uses shared constructs from ../../libs/cdk/)
│   ├── deploy.sh                # Deploy script (bootstraps + creates users)
│   └── outputs.json             # CDK outputs (generated, not committed)
│
├── configure.sh                 # Wrapper: agentcore configure (reads OAuth from SSM)
├── launch.sh                    # Wrapper: agentcore launch + SSM publish
├── health.py                    # Health check (uses ../../libs/python/agentcore_health.py)
├── health.sh                    # Health check wrapper
├── pyproject.toml               # Dependencies
├── .bedrock_agentcore.yaml      # Generated by agentcore CLI (not committed)
└── .dockerignore                # Docker build excludes
```

**Note:** This project depends on shared libraries in `../../libs/`:
- `libs/python/agentcore_health.py` - Shared health check module
- `libs/python/auth_utils.py` - OAuth2/JWT utilities
- `libs/python/ssm_utils.py` - SSM Parameter Store utilities
- `libs/cdk/` - Reusable CDK constructs (AgentExecutionRole, AgentCognito, AgentAppClient)

## Development Dependencies

Key dependencies in `pyproject.toml`:

**Agent frameworks:**
- `strands-agents>=1.7.1` - Main agent framework
- `langgraph>=1.0.1` - Used by financial analysis agent
- `bedrock-agentcore>=0.1.3` - AgentCore Runtime SDK

**Financial tools:**
- `yfinance>=0.2.65` - Stock data retrieval
- `pandas>=2.3.2`, `matplotlib>=3.10.6` - Data analysis and charts

**Vision/documents:**
- `Pillow>=10.0.0` - Image processing
- `PyMuPDF>=1.24.0` - PDF to image (pure Python, no system deps)

**Infrastructure:**
- `aws-cdk-lib`, `constructs` - CDK for Cognito/IAM
- `playwright>=1.40.0` - Browser automation (financial analysis agent)

**Auth:**
- `PyJWT>=2.10.0` - JWT token handling
- `aiohttp` - Required for local mode health checks

## Docker Containerization

The AgentCore CLI automatically handles Docker builds during `./launch.sh` (via `agentcore launch`).

**Container runtime:**
- Base image: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`
- Package manager: UV (for fast dependency installation)
- User: `bedrock_agentcore` (non-root for security)
- Instrumentation: OpenTelemetry for observability

**Dockerfile is auto-generated** by AgentCore CLI based on:
- Entrypoint: `main.py`
- Dependencies: `pyproject.toml`
- Excludes: `.dockerignore` (venvs, cache, test files)

**Build process:**
```bash
./launch.sh
# Internally runs:
# 1. agentcore launch builds Docker image
# 2. Pushes to ECR repository (auto-created)
# 3. Deploys to AgentCore Runtime
# 4. Publishes ARN to SSM Parameter Store
```

**Local testing with Docker:**
```bash
# Run agent locally (HTTP endpoint on localhost:8080)
uv run agentcore launch --local

# Test local endpoint
./health.sh --local
```

## Important Conventions

### Service Discovery

After deployment, configuration is automatically published to SSM:

**Agent ARN:** `/agentcore/finance-personal-assistant/config`
```json
{
  "arn": "arn:aws:bedrock-agentcore:us-west-2:...",
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://...",
      "allowedClients": ["..."]
    }
  }
}
```

**Guardrail config:** `/agentcore/finance-personal-assistant/guardrail-config`
```json
{
  "guardrail_id": "...",
  "version": "1"
}
```

The Streamlit UI (`../../ui/`) reads these parameters for automatic agent discovery - no manual sync required!

### Memory Lifecycle

Memory is created automatically on first invocation (lazy initialization):

```python
def get_memory() -> Memory:
    """Lazy initialization prevents parallel creation race conditions"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = Memory(region_name=region, config=FINANCE_MEMORY_CONFIG)
    return _memory_instance
```

**Memory search:**
- Searches for existing memory by name prefix (`finance_personal_assistant_mem`)
- Reuses existing to preserve historical data
- Waits for ACTIVE status before proceeding
- Event expiry: 90 days (configurable in `FINANCE_MEMORY_CONFIG`)

### Guardrails Best Practices

**Conditional guardrails:**
```python
guardrail_config = get_guardrail_config()  # Returns None if not configured
if guardrail_config:
    # Only apply if guardrails exist
```

**Pre-check pattern:**
- Validate user input BEFORE agent invocation
- Prevents conversation history contamination
- Returns intervention message without calling agent

**Silent redaction:**
- Input redaction: Prevents re-triggering on subsequent turns
- Output redaction: Protects sensitive information
- Seamless UX (no error messages)

### Model Selection

**Default models:**
- Orchestrator: Claude Sonnet 4.5
- Budget Agent: Claude Sonnet 4.5
- Financial Analysis Agent: Claude Sonnet 4.5
- Vision: Nova Premier

**Temperature settings:**
- Claude models: 0.7 (balanced creativity/consistency)
- Nova models: 0.4 (deterministic)
- Vision: 0.1 (accurate extraction)

### Region Configuration

Precedence order (defined in `config.py`):
1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable
3. boto3 session default (`~/.aws/config`)
4. Hardcoded: `us-west-2`

## AWS Configuration

**Required permissions:**
- Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- AgentCore: `bedrock-agentcore:*` (or `BedrockAgentCoreFullAccess` managed policy)
- IAM: CreateRole, DeleteRole, GetRole, PutRolePolicy
- ECR: CreateRepository, GetAuthorizationToken
- CodeBuild: StartBuild, BatchGetBuilds
- CloudWatch Logs, S3
- SSM: GetParameter, PutParameter

**Default profile:**
- `AWS_PROFILE=binbash`
- Verify: `AWS_PROFILE=binbash aws sts get-caller-identity`

**Model access:** No manual configuration needed (October 2025). All serverless models are automatically enabled. For legacy accounts only: enable in [Bedrock Console](https://console.aws.amazon.com/bedrock/home#/modelaccess).

## Typical Development Workflow

### Initial Setup (One-Time)

```bash
# Install dependencies
uv sync

# Set up demo users (optional)
cp ../../.demo_users.json.example .demo_users.json
# Edit with desired usernames/passwords

# Deploy OAuth infrastructure (optional)
cd cdk
./deploy.sh  # Creates Cognito, stores OAuth in SSM
cd ..
```

### Deploy Agent

```bash
# Configure (reads OAuth from SSM if exists)
./configure.sh

# Launch (publishes ARN to SSM automatically)
./launch.sh

# Verify
./health.sh
```

### Iterative Development

```bash
# Make code changes

# Test locally first
uv run python budget_agent.py
uv run python financial_analysis_agent.py

# Redeploy (creates new version)
./launch.sh

# Test deployed
./health.sh
```

## Differences from Workshop

The workshop notebooks (`../workshop/`) are educational, step-by-step implementations. This production version adds:

| Feature | Workshop | Production |
|---------|----------|------------|
| **Memory** | STM only | Multi-strategy (3 strategies) + LTM retrieval |
| **Authentication** | Basic Cognito | CDK-based OAuth2 |
| **Vision** | ❌ | ✅ Amazon Nova Premier |
| **Documents** | ❌ | ✅ CSV/PDF processing |
| **Guardrails** | Basic | Pre-check validation pattern |
| **Deployment** | Manual | Scripted (`configure.sh` + `launch.sh`) |
| **Service Discovery** | Hardcoded ARNs | SSM Parameter Store |
| **Infrastructure** | Manual setup | CDK (reusable shared constructs) |
| **Health Checks** | None | Cascading fallback (AWS → Local) |

## Sample Queries

**Budget queries:**
- "I make $6000/month. Help me create a budget."
- "I spend $800/month on dining. Is this too much for my $5000 income?"

**Investment queries:**
- "Analyze Apple stock and tell me if it's a good investment."
- "Create a moderate risk portfolio for $10,000."

**Multi-agent queries:**
- "I make $5000/month and want to invest $1000. Help me budget and suggest a portfolio."

**Vision queries:**
- Upload receipt + "Track this expense in my budget."
- Upload invoice + "Add this to my monthly spending analysis."

**Document queries:**
- Upload CSV transactions + "Analyze my spending patterns."
- Upload PDF statement + "Extract financial data from this document."

## Troubleshooting

### Health Check Fails

**Symptoms:** `./health.sh` exits with non-zero code or timeout

**Diagnosis:**
```bash
# Check deployment status
uv run agentcore status

# View recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --since 10m

# Verify agent ARN exists
grep agent_arn .bedrock_agentcore.yaml

# Test with increased timeout
./health.sh --timeout 180
```

**Common causes:**
- Agent not deployed: Run `./launch.sh`
- Cold start: First invocation takes 30-60s (subsequent calls faster)
- Region mismatch: Verify `AWS_REGION` matches deployment
- IAM permissions: Ensure `bedrock-agentcore:InvokeAgentRuntime` exists

### Memory Not Working

**Symptoms:** Agent doesn't remember previous conversations

**Diagnosis:**
```bash
# Check memory status
aws bedrock-agentcore list-memories --query "memories[?contains(memoryName, 'finance_personal_assistant')]"

# Verify memory configuration
grep memory_id .bedrock_agentcore.yaml

# Check recent memory events
aws bedrock-agentcore list-memory-events \
    --memory-id "$(grep memory_id .bedrock_agentcore.yaml | awk '{print $2}')" \
    --max-results 5
```

**Solutions:**
```bash
# Reset memory (clears runtime-created memories)
uv run python reset_memory.py

# Verify retrieval config
grep -A 5 "RETRIEVAL_CONFIG" memory_config.py
```

### OAuth Issues

**Symptoms:** Authentication errors when using Cognito

**Diagnosis:**
```bash
# Verify OAuth config in SSM
aws ssm get-parameter --name "/agentcore/finance-personal-assistant/config" | jq '.Parameter.Value | fromjson'

# Check Cognito User Pool
aws cognito-idp list-user-pools --max-results 10
```

**Remove OAuth (revert to IAM):**
```bash
# Delete config parameter
aws ssm delete-parameter --name "/agentcore/finance-personal-assistant/config"

# Reconfigure without OAuth
./configure.sh  # Falls back to IAM auth

# Redeploy
./launch.sh
```

### Docker Build Fails

**Symptoms:** `./launch.sh` fails during image build

**Solutions:**
```bash
# Check Docker daemon
docker info

# Clean Docker cache
docker system prune -f

# Verify ECR authentication
aws ecr get-login-password --region us-west-2 | \
    docker login --username AWS --password-stdin {account-id}.dkr.ecr.us-west-2.amazonaws.com

# Manual rebuild
uv run agentcore launch --auto-update-on-conflict
```

### Import Errors from Shared Libraries

**Symptoms:** `ModuleNotFoundError: No module named 'libs'`

**Solution:**
```bash
# Verify parent path injection in health.py
grep "sys.path.insert" health.py
# Should see: sys.path.insert(0, str(Path(__file__).parent.parent))

# Check shared libraries exist
ls -la ../../libs/python/agentcore_health.py

# Install parent package dependencies
cd ../.. && uv sync
```

### Guardrail Blocking Legitimate Content

**Symptoms:** Agent returns intervention message for valid queries

**Solutions:**
```bash
# Check guardrail configuration
uv run python -c "from config import get_guardrail_config; print(get_guardrail_config())"

# Temporarily disable guardrails
aws ssm delete-parameter --name "/agentcore/finance-personal-assistant/guardrail-config"
./launch.sh  # Redeploy without guardrails

# Modify guardrail policy if needed
# Edit deploy_guardrails.py, then:
uv run python deploy_guardrails.py --create-version
```

## Monitoring

### CloudWatch Logs

```bash
# View agent logs (replace {agent-id} from .bedrock_agentcore.yaml)
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

### Health Checks

```bash
./health.sh                # Cascading: AWS → Local
./health.sh --aws          # Test deployed agent
./health.sh --local        # Test local HTTP (requires: agentcore launch --local)
./health.sh --timeout 120  # Custom timeout
```

### Observability Dashboard

Visit: https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License:** Apache License 2.0 - See LICENSE for details.

**Workshop materials:** https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US
