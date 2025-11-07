# Workshop: Building Multi-Agent Financial Advisors

**Difficulty**: Beginner to Intermediate
**Prerequisites**: AWS account with Bedrock access, Python 3.13+

## 🎓 What You'll Build

A lightweight multi-agent financial advisory system using:
- **Strands Agents** - For building conversational AI agents
- **Amazon Bedrock** - For foundation model access
- **AgentCore Runtime** - For production deployment

By the end, you'll have deployed a working agent to AWS!

---

## 📚 Workshop Structure

### Lab 1: Develop a Personal Budget Assistant
**File**: `lab1-develop_a_personal_budget_assistant_strands_agent.ipynb`

**What you'll learn:**
- Create your first Strands agent
- Add custom tools (budget calculator, financial charts)
- Integrate Bedrock Guardrails for content filtering
- Use conversation managers for context handling
- Generate structured outputs with Pydantic models

**What you'll build:**
- Budget Agent with 50/30/20 budget calculations
- Financial health scoring
- Spending analysis tools

---

### Lab 2: Build Multi-Agent Workflows
**File**: `lab2-build_multi_agent_workflows_with_strands.ipynb`

**What you'll learn:**
- Create specialized agents for different domains
- Build an orchestrator agent that coordinates specialists
- Wrap agents as tools for composition
- Combine insights from multiple agents

**What you'll build:**
- Financial Analysis Agent (stock research, portfolio creation)
- Orchestrator Agent (routes queries to appropriate specialists)
- Multi-agent system with cohesive responses

---

### Lab 3: Deploy to AgentCore Runtime
**File**: `lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb`

**What you'll learn:**
- Prepare agents for production deployment
- Create AgentCore entrypoints with streaming
- Configure Cognito for authentication
- Deploy to AWS with CodeBuild
- Invoke deployed agents via HTTP

**What you'll build:**
- Production-ready Docker container
- AgentCore Runtime deployment
- Authenticated API endpoint

---

## 📓 What is a Jupyter Notebook?

If you're new to Jupyter Notebooks, here's what you need to know:

### Key Concepts

A **Jupyter Notebook** is an interactive document that lets you:
- Write and run code in small chunks called **cells**
- See results immediately below each code cell
- Mix documentation (text, images) with executable code
- Experiment with code without rerunning entire files

### How to Run Code in Notebooks

**Important:** Commands in notebook cells are NOT terminal commands. They run inside the notebook environment.

**To execute a code cell:**
1. Click on the cell to select it
2. Press `Shift+Enter` (or click the ▶️ "Run Cell" button)
3. Wait for output to appear below the cell
4. Move to the next cell

**Cell execution order matters:**
- Run cells from top to bottom in sequence
- Each cell builds on previous cells
- Skipping cells or running out of order may cause errors

### Example Notebook Structure

```
┌──────────────────────────────────┐
│ # Step 1: Import Libraries       │  ← Markdown (documentation)
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ from strands import Agent        │  ← Code cell
│ import boto3                     │  Run this with Shift+Enter
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ (no output)                      │  ← Output cell
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ # Step 2: Test the import        │  ← Markdown
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ print("Setup complete!")         │  ← Code cell
└──────────────────────────────────┘
    ↓
┌──────────────────────────────────┐
│ Setup complete!                  │  ← Output appears here
└──────────────────────────────────┘
```

### Common Notebook Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Run cell and move to next | `Shift+Enter` |
| Run cell and stay | `Ctrl+Enter` |
| Insert cell below | `B` (in command mode) |
| Insert cell above | `A` (in command mode) |
| Delete cell | `D+D` (press D twice) |
| Enter edit mode | `Enter` |
| Exit edit mode | `Esc` |

**Tip:** Press `Esc` to enter "command mode" (cell has blue border), then use keyboard shortcuts. Press `Enter` to edit cell content.

---

## 🚀 Getting Started

### Step 1: Validate Prerequisites

**From the project root**, run the automated validation script:

```bash
cd ../../  # Navigate to genai-agentcore-demos root
./quickstart.sh
```

This checks:
- ✓ AWS CLI and credentials configured
- ✓ Python 3.13+, Docker, AWS CDK installed
- ✓ CDK bootstrapped in your region

**Need help?** See [Pre-Workshop Checklist](../../PRE_WORKSHOP_CHECKLIST.md) for detailed AWS configuration.

---

### Step 2: Install Dependencies

```bash
# Navigate to the main demo folder (where pyproject.toml lives)
cd ../../  # Or: cd genai-agentcore-demos

# Install dependencies
uv sync
```

---

### Step 3: Open Your Editor

**Important:** Open VS Code or Cursor from the `genai-agentcore-demos/` directory, **not** from the workshop subdirectory. This ensures your editor recognizes the virtual environment (`.venv`) and can properly detect the Python kernel for Jupyter notebooks.

**Before opening your editor**, export your AWS profile so the kernel recognizes your AWS account:

```bash
# From genai-agentcore-demos/ directory
export AWS_PROFILE=your-profile-name  # Replace with your AWS profile
cursor .  # Or: code .
```

**Why this matters:** VS Code and Cursor look for virtual environments in the folder you open. If you open a subdirectory (like `workshop/`), they won't find the `.venv` folder that lives at the `genai-agentcore-demos/` level, and you'll have trouble selecting the correct kernel for notebooks.

Once your editor opens, navigate to and click on the notebooks in this order:
1. [Lab 1: Develop a Personal Budget Assistant](lab1-develop_a_personal_budget_assistant_strands_agent.ipynb)
2. [Lab 2: Build Multi-Agent Workflows](lab2-build_multi_agent_workflows_with_strands.ipynb)
3. [Lab 3: Deploy to AgentCore Runtime](lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb)

---

### Step 4: Complete Labs in Order

**⚠️ Important**: Run notebooks sequentially (Lab 1 → Lab 2 → Lab 3) as each builds on the previous.

**Why sequential execution matters:**
- **Lab 2 depends on Lab 1**: The multi-agent orchestrator (Lab 2) imports the budget agent you create in Lab 1
- **Lab 3 depends on Lab 2**: The deployment process (Lab 3) uses the `main.py` orchestrator file generated in Lab 2
- **Conceptual progression**: Each lab introduces new concepts that build on what you learned previously
- **File artifacts**: Notebooks create Python files (`budget_agent.py`, `main.py`) that later labs import and use

1. [**Lab 1**: Develop a Personal Budget Assistant](lab1-develop_a_personal_budget_assistant_strands_agent.ipynb)
   - Build your first Strands agent with custom tools

2. [**Lab 2**: Build Multi-Agent Workflows](lab2-build_multi_agent_workflows_with_strands.ipynb)
   - **Requires**: `budget_agent.py` from Lab 1
   - Create multi-agent orchestration

3. [**Lab 3**: Deploy to AgentCore Runtime](lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb)
   - **Requires**: `main.py` from Lab 2
   - Deploy to AWS AgentCore Runtime

---

## 📁 Workshop Files

```
workshop/
├── README.md (you are here)
├── utils.py (workshop utilities - already provided)
├── images/ (architecture diagrams)
├── lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
├── lab2-build_multi_agent_workflows_with_strands.ipynb
└── lab3-deploy_agents_on_amazon_bedrock_agentcore.ipynb
```

**Note**: Notebooks will create files like `budget_agent.py` and `main.py` during exercises. These are workshop versions and will be gitignored. Don't worry if you see them appear!

---

## 🎯 Learning Objectives

By completing this workshop, you will:

- ✅ Understand core Strands Agents concepts (tools, prompts, conversation management)
- ✅ Build specialized agents for different financial domains
- ✅ Implement multi-agent orchestration patterns
- ✅ Deploy production agents to AWS using AgentCore Runtime
- ✅ Configure authentication with Cognito
- ✅ Stream responses in real-time from deployed agents

---

## 🔄 Workshop vs Production

This workshop uses **lightweight, educational versions** of the agents for learning purposes.

| Feature | Workshop (This Directory) | Production (`../production/`) |
|---------|---------------------------|-------------------------------|
| **Memory** | STM only (auto-created) | Multi-strategy (USER_PREFERENCE, SEMANTIC, SUMMARY) |
| **Authentication** | Basic Cognito (SDK) | CDK-managed with OAuth2 |
| **Document Processing** | Not included | Vision (receipts), CSV/PDF parsing |
| **Deployment** | Manual via SDK | Scripted via configure.sh + launch.sh |
| **Service Discovery** | Hardcoded ARNs | SSM Parameter Store (dynamic) |
| **UI** | None | Streamlit with SSE streaming |
| **Tools** | Basic (calculator, charts) | Advanced (yfinance, browser, memory retrieval) |

**After the workshop**, explore `../production/` to see enterprise-ready implementations with:
- AgentCore Memory with parallel retrieval
- Vision analysis for financial documents
- OAuth2/Cognito via CDK
- Streamlit UI with real-time streaming
- Health checks with cascading fallback
- Comprehensive cleanup and reset utilities

---

## 💡 Tips for Success

1. **Read cell comments carefully** - They explain what each code block does
2. **Run cells in order** - Each notebook builds progressively
3. **Check outputs** - Verify each step completed successfully
4. **Save your work** - Notebooks auto-save, but save manually before closing
5. **Ask questions** - If something is unclear, ask the instructor!

---

## 🧹 Cleanup (After Workshop)

Lab 3 includes cleanup cells (commented out by default). To clean up workshop resources:

```python
# In Lab 3 notebook, uncomment and run:
agentcore_runtime.delete_agent(agent_id=launch_result.agent_id)
delete_cognito_user_pool()
delete_guardrail()
```

Or use the production cleanup script (more comprehensive):
```bash
cd ../production
uv run python cleanup.py
```

---

## 🎉 What's Next?

After completing the workshop:

1. **Explore Production Code**: Check `../production/` for advanced features (multi-strategy memory, vision analysis, OAuth2, etc.)
2. **Try the Streamlit UI**: Run `../../demo.sh` from project root to interact with deployed agents
3. **Customize Agents**: Modify prompts, add new tools, experiment with different models!
4. **Read Production Guide**: See [`../production/README.md`](../production/README.md) for full enterprise deployment details

---

## 📚 Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [AWS Bedrock AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Workshop Slides](https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)

---

## ❓ Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `uv sync` from workshop directory |
| `ModelAccessDeniedException` | Verify IAM permissions (`bedrock:InvokeModel`). For legacy accounts: enable models in Bedrock Console |
| `AccessDeniedException` | Check AWS credentials: `aws sts get-caller-identity` |
| Guardrail creation fails | Verify Bedrock permissions in IAM |
| Agent deployment slow | Normal - CodeBuild build in progress |

### Getting Help

- Check cell outputs for error messages
- Review the troubleshooting section in each notebook
- Ask your workshop instructor
- Check CloudWatch Logs for deployed agent errors

---

## 📄 License

Apache License 2.0 - See [LICENSE](../../LICENSE) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.
