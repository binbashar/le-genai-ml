# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **monorepo** containing three Amazon Bedrock AgentCore demonstration projects showcasing different approaches to building AI agents:

1. **finance-personal-assistant/** - Workshop-based multi-agent system using Strands Agents (Jupyter notebooks)
2. **market-trends-agent/** - Production-ready LangGraph agent with advanced memory management (Python CLI)
3. **streamlit-demo/** - Unified Streamlit interface for event demos, showcasing both agents with real-time streaming (NEW)

All projects demonstrate financial AI agents but use different architectures, frameworks, and deployment patterns.

## Repository Structure

```
genai-agentcore-demos/
├── finance-personal-assistant/    # Workshop: Multi-agent financial advisor
│   ├── lab1-*.ipynb              # Budget agent with Strands
│   ├── lab2-*.ipynb              # Multi-agent orchestration
│   ├── lab3-*.ipynb              # AgentCore deployment
│   ├── utils/                    # Shared utilities (message formatting, guardrails, Cognito)
│   └── requirements.txt          # Strands agents + dependencies
│
├── market-trends-agent/          # Production: Market intelligence agent
│   ├── market_trends_agent.py    # LangGraph agent with memory
│   ├── deploy.py                 # One-command AWS deployment
│   ├── chat.py                   # Interactive streaming chat
│   ├── local_chat.py             # Local testing without deployment
│   ├── tools/                    # Market data, broker profiles, memory
│   └── pyproject.toml            # Modern uv-based dependencies
│
└── streamlit-demo/               # Event demo: Unified Streamlit interface
    ├── app.py                    # Single-file Streamlit application (~100 lines)
    ├── CLAUDE.md                 # Context management instructions
    ├── PRD.md                    # Product requirements (MVP scope)
    ├── requirements.md           # Functional specifications (27 requirements)
    ├── design.md                 # Technical design (50-line pattern)
    ├── tasks.md                  # Implementation tasks (5 strategic tasks)
    └── README.md                 # Setup and demo instructions
```

## Project Comparison

| Aspect | finance-personal-assistant | market-trends-agent | streamlit-demo |
|--------|---------------------------|---------------------|----------------|
| **Framework** | Strands Agents | LangGraph | Streamlit + boto3 |
| **Format** | Jupyter notebooks | Python CLI scripts | Single-file web UI |
| **Purpose** | Educational workshop | Production example | Event demonstration |
| **Agent Type** | Multi-agent orchestration (3 agents) | Single graph agent | Calls both existing agents |
| **Memory** | Basic AgentCore integration | Advanced multi-strategy (STM+LTM) | Stateless (no memory) |
| **Tools** | Budget analysis, stock data | Browser automation, broker profiles | Shows tool orchestration |
| **Deployment** | Manual via notebooks | Automated via deploy.py | Local only (no deployment) |
| **Dependencies** | requirements.txt (pip) | pyproject.toml (uv) | pyproject.toml (uv) |
| **Python Version** | 3.8+ | 3.13+ | 3.13+ |

## Common Development Commands

### finance-personal-assistant (Workshop)

```bash
cd finance-personal-assistant

# Install dependencies
pip install -r requirements.txt

# Launch Jupyter notebooks
jupyter notebook lab1-develop_a_personal_budget_assistant_strands_agent.ipynb

# Run notebooks sequentially
# Lab 1 (20 min): Build Budget Agent
# Lab 2 (20 min): Add Financial Analysis Agent + Orchestrator
# Lab 3 (15 min): Deploy to AgentCore

# Production deployment (without Cognito auth)
uv run agentcore configure --entrypoint main.py --name personal_finance_agent --non-interactive
uv run agentcore launch
```

**Cleanup**: Each notebook has cleanup cells at the end (commented out). Uncomment and run to delete:
- Bedrock Guardrails
- Cognito user pools
- Deployed agents

### market-trends-agent (Production)

```bash
cd market-trends-agent

# Install dependencies
uv sync

# Install Playwright browsers (required)
uv run playwright install

# Deploy to AWS (one command)
uv run python deploy.py

# Interactive chat with deployed agent
uv run python chat.py
uv run python chat.py --debug  # Enable detailed logging

# Local testing (no deployment needed)
uv run python local_chat.py

# Test deployed agent
uv run python test_agent.py

# Clean up all AWS resources
uv run python cleanup.py
```

### streamlit-demo (Event Demo)

```bash
cd streamlit-demo

# Setup environment (one-time)
uv venv
uv sync

# Run the demo
uv run streamlit run app.py

# Important: Update agent ARNs in app.py before running
# The app will open automatically at http://localhost:8501

# Context management: When implementing tasks, always read:
cat PRD.md          # Product vision
cat requirements.md  # Functional specs
cat design.md        # Code patterns
cat tasks.md         # Implementation tasks
```

## Architecture Patterns

### finance-personal-assistant: Multi-Agent Orchestration

**Three-tier architecture**:
1. **Budget Agent** - 50/30/20 budgeting, spending analysis
2. **Financial Analysis Agent** - Stock analysis, portfolio recommendations
3. **Orchestrator Agent** - Routes queries and synthesizes responses

**Key utilities** (`utils/`):
- `message_formatter.py` - Pretty-print agent conversations
- `guardrail.py` - Bedrock guardrails (blocks Bitcoin advice)
- `agentcore_utils.py` - Cognito authentication for deployed agents

**Example usage**:
```python
from utils import pretty_print_messages, create_guardrail

# Display formatted conversation
pretty_print_messages(agent.messages)

# Create guardrail
guardrail_id, guardrail_arn = create_guardrail()
```

### market-trends-agent: LangGraph with Advanced Memory

**Single-agent architecture** with sophisticated memory:
- **LangGraph StateGraph**: Message-based state machine with tool routing
- **Parallel Auto-Injection**: STM + LTM retrieved concurrently via `asyncio.gather()`
- **Multi-Strategy Memory**:
  - USER_PREFERENCE: Broker profiles, risk tolerance
  - SEMANTIC: Financial facts, market insights
- **Session-scoped**: `session_id` (conversation) + `actor_id` (user identity)

**Key components**:
- `market_trends_agent.py` - Agent graph with optimized Claude Sonnet 4 prompt
- `tools/browser_tool.py` - Web scraping for stock data and news
- `tools/broker_card_tools.py` - Structured broker profile management
- `tools/memory_tools.py` - Parallel context retrieval and composition

**Memory pattern**:
```python
# Auto-injection before LLM invocation
stm, ltm = await retrieve_context_parallel(session_id, actor_id)
context_xml = compose_context(stm, ltm)  # <context>...</context>
# Injected into user message automatically
```

### streamlit-demo: Unified Event Interface

**Single-file architecture** for maximum simplicity:
- **Direct API Integration**: Calls existing deployed agents via boto3
- **Real-time Streaming**: SSE parsing for tool visibility and response streaming
- **Stateless Operation**: No session management or memory
- **Hard-coded Configuration**: Demo reliability over flexibility

**Key implementation pattern** (~50 lines total):
```python
# Core streaming loop showing tool orchestration
for line in response["response"].iter_lines():
    if line.startswith(b"data: "):
        event = json.loads(line[6:])
        if event.get("type") == "thinking":
            st.caption(f"🔧 {event.get('message')}")  # Tool visibility
        elif event.get("type") == "stream_token":
            st.write(event.get("token", ""), end="")  # Response streaming
```

**Context Management** (IMPORTANT):
When implementing tasks from `streamlit-demo/tasks.md`, ALWAYS read:
1. `PRD.md` - Product vision and scope
2. `requirements.md` - Functional specifications
3. `design.md` - Technical patterns
4. `tasks.md` - Implementation tasks

This ensures full context is maintained during implementation.

## AWS Services Used

All projects use:
- **Amazon Bedrock** - Foundation models (Claude 3.7 Sonnet / Claude Sonnet 4)
- **Amazon Bedrock AgentCore** - Serverless agent runtime and memory

**finance-personal-assistant** also uses:
- Amazon Bedrock Guardrails - Content policy enforcement
- Amazon Cognito - User authentication for deployed agents

**market-trends-agent** also uses:
- Amazon ECR - Container registry for agent images
- AWS CodeBuild - Container build pipeline
- AWS CloudWatch - Agent runtime logs
- AWS X-Ray - Distributed tracing

**streamlit-demo** uses:
- Only boto3 client calls to existing deployed agents
- No additional AWS services (runs locally)

## Prerequisites

### All Projects
- AWS account with Bedrock access
- AWS CLI configured with credentials
- Model access enabled for Anthropic Claude models on Bedrock

### finance-personal-assistant
- Python 3.8+
- Jupyter Notebook or compatible IDE

### market-trends-agent
- Python 3.13+
- Docker or Podman installed and running
- uv package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### streamlit-demo
- Python 3.13+
- uv package manager
- Both agents deployed and accessible (finance-personal-assistant and market-trends-agent)

## Configuration Files

### finance-personal-assistant
- `requirements.txt` - Auto-generated from pyproject.toml via uv
- No deployment config (manual via notebooks)

### market-trends-agent
- `pyproject.toml` - Modern Python project definition
- `.bedrock_agentcore.yaml` - Auto-generated deployment config
- `.agent_arn` - Deployed runtime ARN (for testing)
- `.memory_id` - Memory instance ID cache

## Sample Queries

### finance-personal-assistant
```
"I make $6000/month and want to invest $500. Help me create a budget and portfolio."
"I spend $800/month on dining and want to invest the savings. What should I do?"
"Compare Tesla and Apple stocks for my $4000 monthly income."
```

### market-trends-agent
```
# First, send broker profile:
Name: Yuval Bing
Company: HSBC
Role: Investment Advisor
Preferred News Feed: BBC
Industry Interests: oil, emerging markets
Investment Strategy: dividend
Risk Tolerance: low

# Then query:
"What's happening with biotech stocks today?"
"Give me an analysis of the AI sector for my tech-focused clients."
```

## Development Workflow

### Working on finance-personal-assistant
1. Navigate to `finance-personal-assistant/`
2. Execute notebooks sequentially in Jupyter
3. Test agent responses in notebook cells
4. Modify utility functions in `utils/` as needed
5. Clean up AWS resources via notebook cleanup cells

### Working on market-trends-agent
1. Navigate to `market-trends-agent/`
2. Make changes to agent logic or tools
3. Test locally: `uv run python local_chat.py`
4. Deploy to AWS: `uv run python deploy.py`
5. Test deployed agent: `uv run python chat.py`
6. Clean up: `uv run python cleanup.py`

## Key Implementation Notes

### Strands Agents vs LangGraph
- **Strands**: Higher-level abstraction, easier multi-agent orchestration
- **LangGraph**: Lower-level control, explicit state graphs, better for complex workflows

### Memory Strategies
- **finance-personal-assistant**: Basic memory via AgentCore integration in Lab 3
- **market-trends-agent**: Advanced dual-layer (STM/LTM) with parallel retrieval

### Deployment Patterns
- **finance-personal-assistant**: Deployed via notebook cells using bedrock-agentcore-starter-toolkit
- **market-trends-agent**: Automated deployment script with IAM role creation, container build, ECR push

### Testing Approaches
- **finance-personal-assistant**: Interactive testing in Jupyter cells
- **market-trends-agent**: Multiple test scripts (`test_agent.py`, `test_local_agent.py`, `chat.py`)

## Troubleshooting

### Common Issues

**Both projects**:
- **Model access denied**: Enable Claude model access in Bedrock console
- **Throttling errors**: Wait between requests or request limit increases
- **AWS credential issues**: Run `aws configure` or check environment variables

**finance-personal-assistant**:
- **Kernel crashes**: Restart Jupyter kernel and rerun from last checkpoint
- **Guardrail conflicts**: Delete existing guardrails via cleanup cells
- **Cognito user pool limits**: Delete old pools in AWS console

**market-trends-agent**:
- **Container build fails**: Ensure Docker/Podman is running
- **Memory duplicates**: Run `uv run python cleanup.py` then redeploy
- **Playwright errors**: Run `uv run playwright install`
- **Chat streaming issues**: Use `--debug` flag to see raw event stream

## Related Documentation

- AWS Workshop: https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US
- Amazon Bedrock AgentCore: https://aws.amazon.com/bedrock/agentcore/
- Strands Agents: https://strandsagents.com/latest/
- LangGraph: https://langchain-ai.github.io/langgraph/

## Claude Code Skills

This repository includes Claude Code Skills for enhanced development capabilities:

### webapp-testing (Official Anthropic Skill)

**Location**: `.claude/skills/webapp-testing/`

**Purpose**: Test local web applications using Playwright for UI verification, debugging, and automated testing.

**Usage**: Ask Claude to test web applications naturally, e.g.:
- "Test if http://localhost:8501 loads correctly"
- "Take a screenshot of the Streamlit demo and verify both agent dropdowns are visible"
- "Check if the Finance agent query button works"

**Security**: Official Anthropic skill, audited and approved for team use. Executes Playwright scripts in headless mode with localhost-only access.

**Dependencies**: Requires Playwright. Install with `pip install playwright && playwright install chromium`

**Context Cost**: ~50 tokens at startup, full skill loads only when testing web apps.

## Project-Specific Documentation

For detailed information about each project's architecture and implementation:
- `finance-personal-assistant/CLAUDE.md` - Workshop utilities and agent architecture
- `market-trends-agent/CLAUDE.md` - LangGraph patterns, memory system, tools
