# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **workshop directory** for the Finance Personal Assistant project. It contains hands-on Jupyter notebooks designed to teach multi-agent system development with AWS Bedrock AgentCore and Strands Agents in a progressive, 1-hour workshop format.

**Important distinction**: This directory contains **educational, lightweight implementations** for learning purposes. The production-ready code with advanced features (memory strategies, vision analysis, CDK infrastructure, Streamlit UI) is located in the parent directory (`../`).

## Workshop Structure

The workshop consists of three sequential labs (notebooks must be completed in order):

1. **Lab 1** (`lab1-develop_a_personal_budget_assistant_strands_agent.ipynb`, 20 min):
   - Build a budget agent with custom tools (50/30/20 calculator, financial charts)
   - Integrate Bedrock Guardrails for content filtering
   - Generate structured outputs with Pydantic models
   - Use conversation managers for context handling

2. **Lab 2** (`lab2-build_multi_agent_workflows_with_strands.ipynb`, 20 min):
   - Create a financial analysis agent (stock research, portfolio creation)
   - Build an orchestrator agent that coordinates specialists
   - Wrap agents as tools for composition
   - Combine insights from multiple agents

3. **Lab 3** (`lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb`, 15 min):
   - Prepare agents for production deployment
   - Create AgentCore entrypoints with streaming
   - Configure Cognito for authentication via SDK
   - Deploy to AWS with CodeBuild
   - Invoke deployed agents via HTTP

## Common Commands

### Setup

```bash
# Install dependencies (from workshop directory)
uv sync

# Note: This resolves to ../production/pyproject.toml
# All workshop dependencies are inherited from the production project
```

### Running Notebooks

```bash
# Option 1: Jupyter Lab (recommended)
jupyter lab

# Then open notebooks in order:
# - lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
# - lab2-build_multi_agent_workflows_with_strands.ipynb
# - lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb

# Option 2: VS Code
code lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
```

### Post-Workshop Cleanup

Lab 3 includes cleanup cells (commented out by default). To clean up workshop resources:

```python
# In Lab 3 notebook, uncomment and run:
agentcore_runtime.delete_agent(agent_id=launch_result.agent_id)
delete_cognito_user_pool()
delete_guardrail()
```

Or use the comprehensive production cleanup:

```bash
cd ../production
uv run python cleanup.py
```

## Architecture Patterns

### Workshop vs Production Differences

This workshop uses **simplified implementations** to focus on core concepts:

| Component | Workshop (This Directory) | Production (`../`) |
|-----------|---------------------------|-------------------|
| **Memory** | Auto-created STM only | Multi-strategy LTM (USER_PREFERENCE, SEMANTIC, SUMMARY) |
| **Authentication** | SDK-based Cognito (utility functions) | CDK-managed OAuth2 with post-deployment scripts |
| **Document Processing** | Not included | Vision (Nova Premier), CSV/PDF parsing with security |
| **Deployment** | Manual via `bedrock_agentcore.client` SDK | Scripted via `configure.sh` + `launch.sh` |
| **Tools** | Basic (calculator, charts) | Advanced (yfinance, browser automation, memory retrieval) |
| **Service Discovery** | Hardcoded agent ARNs | SSM Parameter Store (dynamic discovery) |
| **Guardrails** | Bitcoin-only topic filter | Comprehensive (gambling, PII, contextual grounding) |

### Utility Module (`utils.py`)

Provides workshop-specific utilities (not used in production):

**Guardrails:**
- `create_guardrail()` - Creates "guardrail-no-bitcoin-advice" (DENY Bitcoin investment queries)
- `delete_guardrail()` - Cleanup workshop guardrail
- `get_guardrail_id()` - Retrieve guardrail ID if exists

**Cognito Authentication:**
- `setup_cognito_user_pool()` - Creates user pool, app client, test user, returns bearer token
- `delete_cognito_user_pool()` - Cleanup workshop Cognito resources
- `reauthenticate_user()` - Get fresh bearer token for API calls

**Helpers:**
- `pretty_print_messages(messages)` - Format conversation history for readability

**Usage pattern in notebooks:**
```python
from utils import create_guardrail, setup_cognito_user_pool

# Lab 1: Create guardrail
guardrail_id, guardrail_arn = create_guardrail()

# Lab 3: Setup authentication
cognito_config = setup_cognito_user_pool()
bearer_token = cognito_config["bearer_token"]
```

### Agent Patterns in Notebooks

**Lab 1 - Budget Agent:**
```python
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager

@tool
def calculate_budget(income: float) -> dict:
    """50/30/20 budget calculator"""
    return {"needs": income * 0.5, "wants": income * 0.3, "savings": income * 0.2}

budget_agent = Agent(
    model=model,
    system_prompt="You are a budget advisor...",
    tools=[calculate_budget],
    conversation_manager=SummarizingConversationManager(),
    guardrail_id=guardrail_id,
    guardrail_version="DRAFT",
    guardrail_trace="enabled"
)

# Structured output
result = budget_agent.structured_output(
    output_model=FinancialReport,
    prompt="Create budget for $6000/month income"
)
```

**Lab 2 - Multi-Agent Orchestration:**
```python
# Wrap specialists as tools
@tool
def budget_agent_tool(query: str) -> str:
    """Delegate budgeting queries"""
    return budget_agent(query)

@tool
def financial_analysis_tool(query: str) -> str:
    """Delegate investment queries"""
    return financial_analysis_agent(query)

# Orchestrator coordinates both
orchestrator = Agent(
    model=model,
    system_prompt="Route queries to appropriate specialist...",
    tools=[budget_agent_tool, financial_analysis_tool]
)
```

**Lab 3 - AgentCore Deployment:**
```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload):
    """AgentCore entrypoint with streaming"""
    prompt = payload["prompt"]
    async for event in agent.stream_async(prompt):
        yield event

# Deploy with SDK
from bedrock_agentcore.client import BedrockAgentCoreRuntime

agentcore_runtime = BedrockAgentCoreRuntime(region_name="us-west-2")
launch_result = agentcore_runtime.launch_agent(
    entrypoint_file="main.py",
    authentication_config={
        "customJWTAuthorizer": {
            "discoveryUrl": cognito_config["discovery_url"],
            "allowedClients": [cognito_config["client_id"]]
        }
    }
)
```

## Generated Files

During the workshop, notebooks will create the following files (all gitignored):

- `budget_agent.py` - Lab 1 output (budget agent code)
- `financial_analysis_agent.py` - Lab 2 output (investment agent code)
- `main.py` - Lab 2/3 output (orchestrator agent)
- `.bedrock_agentcore.yaml` - Lab 3 output (deployment metadata)
- `Dockerfile` - Lab 3 output (container definition, auto-generated)
- `.dockerignore` - Lab 3 output (auto-generated)
- `outputs.json` - Lab 3 output (deployment outputs)

**These files are workshop artifacts and should not be confused with production code in the parent directory.**

## Dependencies

The workshop directory does not have its own `pyproject.toml`. When running `uv sync` from the workshop directory, it resolves dependencies from the parent project:

**Primary dependencies** (from `../production/pyproject.toml`):
- `strands-agents>=1.7.1` - Main agent framework
- `bedrock-agentcore>=0.1.3` - AgentCore Runtime SDK
- `bedrock-agentcore-starter-toolkit>=0.1.10` - Helper utilities
- `langgraph>=1.0.1` - Graph workflows (for financial analysis agent)
- `boto3` - AWS SDK (Cognito, Bedrock, AgentCore)
- `yfinance>=0.2.65` - Stock data (for financial analysis tools)

**Shared utilities** (from `../../pyproject.toml`):
- Available via parent package `genai-agentcore-demos`

**Notebook environment:**
- Jupyter Lab or VS Code with Jupyter extension

## Important Conventions

### Notebook Execution Order

**CRITICAL**: Notebooks must be run sequentially (Lab 1 → Lab 2 → Lab 3) as each builds on previous outputs:
- Lab 2 imports `budget_agent.py` created in Lab 1
- Lab 3 uses `main.py` (orchestrator) created in Lab 2

### Authentication in Lab 3

Workshop uses **SDK-based Cognito setup** (via `utils.setup_cognito_user_pool()`), while production uses **CDK-based infrastructure** (see `../cdk/`).

**Workshop pattern:**
```python
# Create resources via SDK
cognito_config = setup_cognito_user_pool()
bearer_token = cognito_config["bearer_token"]

# Use in deployment
authentication_config = {
    "customJWTAuthorizer": {
        "discoveryUrl": cognito_config["discovery_url"],
        "allowedClients": [cognito_config["client_id"]]
    }
}
```

**Production pattern:**
```bash
# CDK deploys infrastructure
cd cdk && ./deploy.sh

# Agent reads OAuth from SSM Parameter Store
cd .. && ./configure.sh && ./launch.sh
```

### Memory Management

Workshop uses **auto-created STM** (short-term memory) only. Production uses **three-strategy LTM** (long-term memory):
- USER_PREFERENCE: Financial goals, risk tolerance
- SEMANTIC: Budget facts, spending patterns
- SUMMARY: Conversation outcomes

Workshop memory is ephemeral (per-session), production memory persists across sessions with DynamoDB backend.

### Model Selection

Workshop defaults to **us-west-2** region and uses inference profiles:
- Budget Agent: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250514-v1:0`)
- Financial Analysis Agent: Claude Sonnet 4.5
- Vision (production only): Nova Premier (`us.amazon.nova-premier-v1:0`)

### AWS Configuration

**Required before workshop:**
1. AWS credentials configured: `aws sts get-caller-identity`
2. Bedrock model access: As of October 2025, all models are automatically enabled. For legacy accounts only: https://console.aws.amazon.com/bedrock/home#/modelaccess
3. IAM permissions: Bedrock, AgentCore, Cognito, IAM role management

**Default region**: `us-west-2` (hardcoded in `utils.py` functions)

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `uv sync` from workshop directory |
| `ModelAccessDeniedException` | Verify IAM permissions (`bedrock:InvokeModel`). For legacy accounts: enable models in Bedrock Console |
| `AccessDeniedException` | Check AWS credentials: `aws sts get-caller-identity` |
| Guardrail creation fails | Verify Bedrock permissions in IAM |
| Agent deployment slow | Normal - CodeBuild takes 2-3 minutes |
| Cell execution order error | Restart kernel, run cells from top |
| Import error for generated files | Ensure previous lab completed successfully |

### Cleanup Verification

After cleanup, verify resources removed:

```bash
# Check AgentCore Runtimes
aws bedrock-agentcore list-agent-runtimes --region us-west-2

# Check Cognito User Pools
aws cognito-idp list-user-pools --max-results 10 --region us-west-2

# Check Guardrails
aws bedrock list-guardrails --region us-west-2
```

## Relationship to Production Code

After completing the workshop, explore the production implementation in the parent directory (`../`):

**Production enhancements not in workshop:**
- Multi-strategy AgentCore Memory with parallel retrieval (`../production/memory_config.py`, `../production/utils/memory_retrieval.py`)
- Vision analysis for receipts/invoices (`../production/utils/vision_analyzer.py`, Amazon Nova Premier)
- Document processing (CSV formula injection prevention, PDF parsing via PyMuPDF)
- CDK-managed OAuth2 infrastructure (`../production/cdk/`)
- Streamlit UI with SSE streaming, session history, agent discovery via SSM (`../../ui/`)
- Health checks with cascading fallback (AWS → Local) (`../production/health.py`, `../../libs/python/agentcore_health.py`)
- Comprehensive cleanup and memory reset utilities (`../production/cleanup.py`, `../production/reset_memory.py`)
- Service discovery via SSM Parameter Store (`../../libs/python/ssm_utils.py`)
- Shared CDK constructs (`../../libs/cdk/`)

**Key architectural differences:**
- Workshop: Single-file agents, manual SDK deployment, ephemeral memory
- Production: Modular architecture, scripted deployment, persistent multi-strategy memory

## Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [AWS Bedrock AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Workshop Slides](https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)

## License

Apache License 2.0 - See [LICENSE](../../../LICENSE) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.
