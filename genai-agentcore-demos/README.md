# GenAI AgentCore Demos

Production-ready multi-agent financial advisory system built with AWS Bedrock AgentCore and Strands Agents. Workshop-ready codebase demonstrating specialized agents coordinating through intelligent orchestration.

---

## What You'll Build

A complete financial advisory system with:

- **Budget Agent**: Analyzes spending, creates 50/30/20 budgets, provides savings recommendations
- **Investment Agent**: Researches stocks, analyzes market trends, creates investment portfolios
- **Orchestrator**: Routes queries to the right specialist and synthesizes multi-agent responses
- **Interactive UI**: Streamlit demo with real-time streaming, vision analysis, and document processing

**Two Learning Paths:**

1. **🎓 Workshop Mode** - Learn fundamentals with Jupyter notebooks
2. **🚀 Production Mode** - Deploy enterprise-ready agents with OAuth2, vision AI, and advanced memory

---

## Quick Start

### Prerequisites

**⚠️ PREREQUISITE: Complete all setup steps before workshop**

👉 **[Pre-Workshop Checklist](PRE_WORKSHOP_CHECKLIST.md)**

This comprehensive guide covers:
- Creating your AWS account
- Installing AWS CLI, Python, Docker, CDK
- Configuring credentials and bootstrapping CDK
- Verifying your complete setup

**💰 Workshop Cost:** Less than $1 per session

---

### For Workshop Participants

**Step 1: Validate Prerequisites**

After completing the [Pre-Workshop Checklist](PRE_WORKSHOP_CHECKLIST.md), run our automated validation script:

```bash
cd genai-agentcore-demos
./quickstart.sh
```

This checks:
- ✓ AWS CLI and credentials configured
- ✓ Python 3.13+, Docker, AWS CDK installed
- ✓ CDK bootstrapped in your region

**Step 2: Start the Workshop**

```bash
# Install dependencies
cd genai-agentcore-demos
uv sync

# Open your editor at the project root (where .venv lives)
cursor .  # Or: code .
```

**Important:** Open VS Code or Cursor from the `genai-agentcore-demos/` directory (not from subdirectories). This ensures your editor can find the virtual environment (`.venv`) and properly detect Python kernels for the Jupyter notebooks.

Once your editor opens, navigate to the workshop notebooks:
1. [Lab 1: Develop a Personal Budget Assistant](finance-personal-assistant/workshop/lab1-develop_a_personal_budget_assistant_strands_agent.ipynb)
2. [Lab 2: Build Multi-Agent Workflows](finance-personal-assistant/workshop/lab2-build_multi_agent_workflows_with_strands.ipynb)
3. [Lab 3: Deploy to AgentCore Runtime](finance-personal-assistant/workshop/lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb)

---

### Ready to Start the Workshop?

**🎓 Begin with Lab 1:**

Once your setup is validated, start the hands-on labs:

```bash
# Navigate to workshop directory
cd finance-personal-assistant/workshop

# Open your IDE (from genai-agentcore-demos/ root for kernel detection)
cd ../..
cursor .  # Or: code .
```

**📓 Open the notebooks in order:**

1. [Lab 1: Develop a Personal Budget Assistant](finance-personal-assistant/workshop/lab1-develop_a_personal_budget_assistant_strands_agent.ipynb)
2. [Lab 2: Build Multi-Agent Workflows](finance-personal-assistant/workshop/lab2-build_multi_agent_workflows_with_strands.ipynb)
3. [Lab 3: Deploy to AgentCore Runtime](finance-personal-assistant/workshop/lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb)

**💡 IDE Tip:** Click on the links above (or navigate in your IDE's file explorer) to open each notebook. Make sure you've opened the editor from the `genai-agentcore-demos/` directory so it can detect the Python kernel.

👉 **[Workshop Instructions](finance-personal-assistant/workshop/README.md)** - Detailed lab guide

---

### Want to Deploy Production Agents?

After completing the workshop, explore the production implementation with enterprise features:

- Multi-strategy memory (USER_PREFERENCE, SEMANTIC, SUMMARY)
- Vision analysis for receipts/invoices (Amazon Nova Premier)
- OAuth2/Cognito authentication via CDK
- Streamlit UI with real-time streaming
- Document processing (CSV/PDF)
- Service discovery via SSM Parameter Store

👉 **[Production Deployment Guide](finance-personal-assistant/production/README.md)** - Full production setup

---

## Repository Structure

```
genai-agentcore-demos/
├── quickstart.sh              # ⚡ Automated prerequisites validation
├── demo.sh                    # 🎨 Launch Streamlit UI
│
├── finance-personal-assistant/
│   ├── workshop/              # 🎓 Hands-on labs (Jupyter notebooks)
│   │   ├── lab1-*.ipynb       # Budget agent with tools
│   │   ├── lab2-*.ipynb       # Multi-agent orchestration
│   │   └── lab3-*.ipynb       # AgentCore deployment
│   │
│   └── production/            # 🚀 Enterprise system
│       ├── main.py            # Orchestrator (AgentCore entrypoint)
│       ├── budget_agent.py    # Budget specialist
│       ├── financial_analysis_agent.py  # Investment specialist
│       ├── configure.sh       # Setup deployment config
│       ├── launch.sh          # Deploy to AWS
│       └── health.sh          # Health checks
│
├── ui/                        # 🎨 Streamlit demo UI
│   ├── app.py                 # Main application
│   ├── config/agents.yaml     # Agent metadata
│   └── demo.sh                # Launch script
│
├── libs/                      # 📦 Shared libraries
│   ├── python/                # Runtime utilities
│   │   ├── agentcore_health.py   # Health check module
│   │   ├── auth_utils.py         # OAuth2/JWT
│   │   └── ssm_utils.py          # Service discovery
│   └── cdk/                   # Reusable CDK constructs
│
└── scripts/                   # 🛠️ Root-level utilities
    ├── health.sh              # Test all agents
    ├── demo.sh                # Launch UI
    └── reset_memory.sh        # Clear agent memory
```

---

## Workshop vs Production

| Feature | Workshop | Production |
|---------|----------|------------|
| **Purpose** | Learn concepts | Deploy production system |
| **Format** | Jupyter notebooks | Python scripts + CDK |
| **Memory** | Auto-created STM | 3-strategy LTM (USER_PREFERENCE, SEMANTIC, SUMMARY) |
| **Authentication** | Basic Cognito (SDK) | CDK-managed OAuth2 |
| **Vision Analysis** | ❌ | ✅ Amazon Nova Premier |
| **Document Processing** | ❌ | ✅ CSV/PDF with security |
| **Deployment** | Manual via notebooks | Scripted (`configure.sh` + `launch.sh`) |
| **UI** | None | Streamlit with SSE streaming |
| **Service Discovery** | Hardcoded ARNs | SSM Parameter Store (dynamic) |

**Recommendation:** Start with workshop to learn fundamentals, then explore production for enterprise features.

---

## Common Commands

### Health Checks

```bash
# Check all agents (from project root)
./health.sh

# Check specific agent
cd finance-personal-assistant/production
./health.sh                    # Cascading fallback (AWS → Local)
./health.sh --aws              # Test deployed agent only
./health.sh --local            # Test local endpoint
./health.sh --timeout 120      # Custom timeout
```

### Memory Management

```bash
# Reset memory (clears runtime-created memories)
cd finance-personal-assistant/production
uv run reset_memory.py

# Or from project root
./reset_memory.sh --agent finance-personal-assistant
```

### Cleanup

```bash
cd finance-personal-assistant/production

# Preview deletions
uv run cleanup.py --dry-run

# Complete cleanup
uv run cleanup.py

# Keep IAM roles
uv run cleanup.py --skip-iam
```

Removes: Runtime, Memory, ECR, CodeBuild, S3, SSM parameters, IAM roles, `.bedrock_agentcore.yaml`

---

## Sample Queries

Try these queries in the Streamlit UI or deployed agent:

**Budget Queries:**
- "I make $6000/month. Help me create a budget and start investing $500/month."
- "I spend $800/month on dining. How can I cut back and save more?"

**Investment Queries:**
- "Analyze Apple stock and tell me if it's a good investment."
- "Create a moderate risk portfolio for $10,000."

**Multi-Agent Queries:**
- "I earn $5000/month and want to invest $1000. Help me budget and suggest a portfolio."

**Vision Queries** (Production only):
- Upload receipt image + "Track this expense in my budget."

---

## Architecture Highlights

### Multi-Agent Orchestration

The orchestrator wraps specialist agents as tools:

```python
@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Budget planning and spending analysis"""
    return budget_agent.structured_output(output_model=FinancialReport, prompt=query)

@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Investment research and portfolio creation"""
    return financial_analysis_agent(query)

orchestrator_agent = Agent(
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=SummarizingConversationManager(),
    session_manager=session_manager  # AgentCore Memory integration
)
```

### Memory Strategies (Production)

Three-strategy memory pattern for comprehensive context retrieval:

1. **USER_PREFERENCE**: User profile (name, goals, risk tolerance)
2. **SEMANTIC**: Financial facts (budgets, income, spending patterns)
3. **SUMMARY**: Conversation summaries (session outcomes)

Memories retrieved in parallel and injected into agent prompts automatically.

### Service Discovery via SSM

Agents publish configuration to SSM Parameter Store after deployment:

```bash
./launch.sh  # Automatically publishes to /agentcore/finance-personal-assistant/config
```

Streamlit UI discovers agents at runtime - no manual sync required!

---

## Troubleshooting

### Quickstart Script Fails

Run the validation script to identify issues:

```bash
./quickstart.sh
```

Common fixes:
- **AWS credentials not configured**: `aws configure sso` or `aws configure`
- **Docker not running**: Start Docker Desktop
- **CDK not bootstrapped**: `cdk bootstrap aws://ACCOUNT_ID/REGION`

### Deployment Issues

**Health check fails:**

```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# Check deployment status
cd finance-personal-assistant/production
uv run agentcore status
```

**Memory not working:**

```bash
# Verify memory is ACTIVE
aws bedrock-agentcore list-memories

# Reset memory if needed
uv run reset_memory.py
```

**OAuth configuration issues:**

```bash
# Verify OAuth config in SSM
aws ssm get-parameter --name "/agentcore/finance-personal-assistant/config"

# Remove OAuth (revert to IAM)
aws ssm delete-parameter --name "/agentcore/finance-personal-assistant/config"
./configure.sh  # Reconfigure without OAuth
```

> **More Help:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive troubleshooting guide.

---

## Documentation

- [Pre-Workshop Checklist](PRE_WORKSHOP_CHECKLIST.md) - Complete setup guide with AWS configuration, tools installation, and verification
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Workshop README](finance-personal-assistant/workshop/README.md) - Lab-specific instructions
- [Production README](finance-personal-assistant/production/README.md) - Enterprise deployment details

**External Resources:**
- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [AWS Bedrock AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Workshop Materials](https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)

---

## License

Apache License 2.0 - See [LICENSE](LICENSE.txt) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.
