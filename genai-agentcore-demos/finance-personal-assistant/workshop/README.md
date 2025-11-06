# Workshop: Building Multi-Agent Financial Advisors

**Duration**: 1 hour
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

### Lab 1: Develop a Personal Budget Assistant (20 minutes)
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

### Lab 2: Build Multi-Agent Workflows (20 minutes)
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

### Lab 3: Deploy to AgentCore Runtime (15 minutes)
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

## 🚀 Getting Started

### Prerequisites Check

Ensure you have:
- Python 3.13+ installed
- AWS credentials configured
- Model access: As of October 2025, all Bedrock models are automatically enabled. For legacy accounts only, enable Claude and Nova models in Bedrock Console.

### Installation

```bash
# From this directory (workshop/)
uv sync
```

### Running the Labs

Open the notebooks in order:

```bash
# Option 1: Jupyter Lab
jupyter lab

# Option 2: VS Code
code lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
```

**Important**: Run notebooks in order (Lab 1 → Lab 2 → Lab 3) as each builds on the previous.

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

✅ Understand core Strands Agents concepts (tools, prompts, conversation management)
✅ Build specialized agents for different financial domains
✅ Implement multi-agent orchestration patterns
✅ Deploy production agents to AWS using AgentCore Runtime
✅ Configure authentication with Cognito
✅ Stream responses in real-time from deployed agents

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

1. **Explore Production Code**: Check `../production/` for advanced features
2. **Try the Streamlit UI**: `cd ../production && ./demo.sh`
3. **Customize Agents**: Modify prompts, add new tools, experiment!
4. **Read Documentation**: See `../README.md` for full deployment guide

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
| Agent deployment slow | Normal - CodeBuild can take 2-3 minutes |

### Getting Help

- Check cell outputs for error messages
- Review the troubleshooting section in each notebook
- Ask your workshop instructor
- Check CloudWatch Logs for deployed agent errors

---

## 📄 License

Apache License 2.0 - See [LICENSE](../../LICENSE) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.
