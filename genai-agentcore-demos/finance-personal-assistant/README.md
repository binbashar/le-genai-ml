# Finance Personal Assistant

**Multi-agent financial advisory system** built with AWS Bedrock AgentCore and Strands Agents.

This repository contains two implementations designed for different purposes:

## 📂 Repository Structure

```
finance-personal-assistant/
│
├── workshop/          🎓 Workshop materials for learning
│   ├── Jupyter notebooks (Lab 1, 2, 3)
│   ├── Workshop utilities
│   └── Architecture diagrams
│
├── production/        🚀 Production-ready deployment
│   ├── Multi-agent orchestrator
│   ├── Memory strategies
│   ├── Vision & document processing
│   └── CDK infrastructure
│
└── README.md         📖 This file
```

---

## 🎓 Workshop: Learn Multi-Agent Systems

**Start here if you want to learn** how to build multi-agent systems from scratch.

**Location**: [`workshop/`](./workshop/)

### What You'll Build

A lightweight multi-agent financial advisor with:
- Budget analysis agent
- Investment research agent
- Orchestrator that coordinates both

### Workshop Structure

| Lab | Focus |
|-----|-------|
| **Lab 1** | Build a budget agent with tools and structured outputs |
| **Lab 2** | Create multi-agent orchestration |
| **Lab 3** | Deploy to AgentCore Runtime with Cognito |

### Getting Started

```bash
# Install dependencies from the main demo folder
cd ../../genai-agentcore-demos  # Or navigate to where pyproject.toml lives
uv sync

# Open your editor at this level (where .venv is located)
cursor .  # Or: code .

# Then navigate to and open:
# finance-personal-assistant/workshop/lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
```

**Note:** Open VS Code/Cursor from `genai-agentcore-demos/` (not subdirectories) so your editor can find the virtual environment and detect notebook kernels.

**Full workshop guide**: [workshop/README.md](./workshop/README.md)

---

## 🚀 Production: Enterprise-Grade Deployment

**Use this if you need** a production-ready implementation with advanced features.

**Location**: [`production/`](./production/)

### Features

✅ **Multi-Agent Orchestration** - Specialized agents for budgeting and investments
✅ **AgentCore Memory** - Multi-strategy context retrieval (USER_PREFERENCE, SEMANTIC, SUMMARY)
✅ **Vision Analysis** - Process receipts and invoices with Amazon Nova Premier
✅ **Document Processing** - CSV and PDF parsing with security sanitization
✅ **OAuth2 Authentication** - Production Cognito integration via CDK
✅ **Service Discovery** - SSM Parameter Store for dynamic configuration
✅ **Streaming Responses** - Real-time SSE streaming
✅ **Guardrails** - Content filtering and PII protection

### Quick Start

```bash
cd production/

# Install dependencies
uv sync

# Optional: Deploy OAuth infrastructure
cd cdk && ./deploy.sh && cd ..

# Configure agent
./configure.sh

# Deploy to AWS
./launch.sh

# Verify
./health.sh
```

**Full production guide**: [production/README.md](./production/README.md)

---

## 🔄 Key Differences

| Feature | Workshop | Production |
|---------|----------|------------|
| **Purpose** | Learning & education | Enterprise deployment |
| **Memory** | STM only (auto-created) | Multi-strategy (3 strategies) |
| **Authentication** | Basic Cognito | CDK-managed OAuth2 |
| **Vision** | ❌ Not included | ✅ Amazon Nova Premier |
| **Documents** | ❌ Not included | ✅ CSV/PDF processing |
| **Deployment** | Manual (notebooks) | Scripted (configure.sh + launch.sh) |
| **Service Discovery** | Hardcoded ARNs | SSM Parameter Store |
| **UI** | ❌ None | ✅ Streamlit with streaming |
| **Tools** | Basic (calculator, charts) | Advanced (yfinance, browser, memory) |

---

## 🎯 Multi-Agent Architecture

Our system consists of three core components:

### 1. Budget Agent
*Specializes in personal budgeting, spending analysis, and financial discipline*

| Tool | Description |
|------|-------------|
| **calculate_budget_breakdown** | 50/30/20 budget calculations |
| **analyze_spending_pattern** | Spending analysis with recommendations |
| **calculator** | Financial calculations |

### 2. Financial Analysis Agent
*Focuses on investment research, portfolio management, and market analysis*

| Tool | Description |
|------|-------------|
| **get_stock_analysis** | Real-time stock data and analysis |
| **create_diversified_portfolio** | Risk-based portfolio recommendations |
| **compare_stock_performance** | Multi-stock performance comparison |

### 3. Orchestrator Agent
*Coordinates specialized agents and synthesizes comprehensive responses*

| Capability | Description |
|------------|-------------|
| **Agent Routing** | Determines which specialist(s) to consult |
| **Multi-Agent Coordination** | Combines insights from multiple agents |
| **Response Synthesis** | Creates coherent responses |
| **Context Management** | Maintains conversation flow |

![Architecture](./workshop/images/architecture.png)

---

## 🚦 Which Should I Use?

### Use **Workshop** if you:
- Want to learn multi-agent concepts from scratch
- Are attending or leading a training session
- Need hands-on Jupyter notebook tutorials
- Want to build and deploy a working agent step-by-step

### Use **Production** if you:
- Need a production-ready deployment
- Want advanced features (memory, vision, OAuth)
- Are building an enterprise application
- Need infrastructure-as-code with CDK

### Use **Both** (Recommended):
1. Start with workshop to learn concepts
2. Explore production to see enterprise implementation
3. Use production code as reference for your own projects

---

## 📋 Prerequisites

Both implementations require:

- **Python 3.13+**
- **AWS CLI v2** configured with your own AWS profile
- **Docker** (for production deployments)
- **AWS CDK v2** (for production infrastructure)
- **uv** package manager

### AWS Profile Configuration

**Configure your AWS IAM user credentials** (provided by your workshop administrator):

```bash
# Configure IAM user profile
aws configure --profile workshop

# Enter when prompted:
# - AWS Access Key ID: (provided by administrator)
# - AWS Secret Access Key: (provided by administrator)
# - Default region: us-west-2
# - Output format: json

# Set as default for this session
export AWS_PROFILE=workshop

# Verify credentials
aws sts get-caller-identity
```

**Organizations using AWS SSO:** If your organization requires AWS SSO (IAM Identity Center), configure SSO credentials using `aws configure sso` as detailed in the [Pre-Workshop Checklist](../../PRE_WORKSHOP_CHECKLIST.md).

**Note:** Throughout this documentation, replace any reference to `AWS_PROFILE=binbash` with your configured profile name. For detailed setup instructions, see [Pre-Workshop Checklist](../../PRE_WORKSHOP_CHECKLIST.md).

---

## 💡 Sample Queries

### Budget Queries
- "I make $6000/month and want to start investing $500/month. Help me create a budget."
- "I spend too much on dining out ($800/month). How can I cut back?"
- "Create a comprehensive financial report for someone earning $4000/month."

### Investment Queries
- "Analyze Apple stock and tell me if it's a good investment."
- "Create a moderate risk portfolio for $10,000."
- "Compare Tesla, Apple, and Google stocks over the last 6 months."

### Multi-Agent Queries
- "I make $5000/month and want to invest $1000. Help me budget and suggest a portfolio."
- "Analyze my $800 dining expenses, then recommend stocks to invest my savings."

### Vision Queries (Production Only)
- Upload receipt + "Track this expense in my budget."
- Upload invoice + "Add this to my monthly spending analysis."

---

## 🧹 Cleanup

### Workshop Cleanup

#### Automated Cleanup (Recommended)
```bash
# In Lab 3 notebook, uncomment and run cleanup cells
agentcore_runtime.delete_agent(agent_id=launch_result.agent_id)
delete_cognito_user_pool()
delete_guardrail()
```

#### Manual Cleanup (If Notebooks Are Unavailable)

If you cannot execute the notebook cleanup cells, follow these manual steps using either the AWS Console (recommended for most users) or AWS CLI.

##### Option 1: AWS Console (Recommended)

**1. Delete Cognito Users (Security Critical)** ⚠️

1. Navigate to [Amazon Cognito Console](https://console.aws.amazon.com/cognito/)
2. Click **User Pools** in the left navigation
3. Select your workshop user pool (e.g., `FinanceAssistantUserPool`)
4. Click the **Users** tab
5. **Delete each user individually**:
   - Select a user by clicking the checkbox
   - Click **Delete** button
   - Confirm deletion in the dialog
   - Repeat for all users
6. Verify all users are deleted before proceeding

📖 [AWS Docs: Tutorial - Cleaning up AWS Resources (Cognito)](https://docs.aws.amazon.com/cognito/latest/developerguide/tutorial-cleanup-tutorial.html)

**2. Delete Cognito User Pool**

1. While still in the user pool details page
2. Click the **Delete** button (top right)
3. Type the user pool name to confirm deletion
4. Click **Delete** to permanently remove the pool

📖 [AWS Docs: User Pool Deletion Protection](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-deletion-protection.html)

**3. Delete AgentCore Runtime**

1. Navigate to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. In the left navigation, expand **Agentic** section
3. Click **Agent Runtimes**
4. Find your workshop agent (check the name or tags)
5. Select the agent by clicking the checkbox
6. Click **Delete** button
7. Confirm deletion in the dialog

📖 [AWS Docs: What is Amazon Bedrock AgentCore?](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)

**4. Delete Bedrock Guardrail (Optional)**

1. In the Bedrock Console, click **Guardrails** in the left navigation
2. Find your workshop guardrail
3. Select the guardrail by clicking the checkbox
4. Click **Delete** button
5. Confirm deletion in the dialog

📖 [AWS Docs: Deleting Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-delete.html)

##### Option 2: AWS CLI

**1. Delete Cognito Users (Security Critical)**
```bash
# List all users in the user pool
aws cognito-idp list-users \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --profile <YOUR_PROFILE>

# Delete each user individually
aws cognito-idp admin-delete-user \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --username <USERNAME> \
  --profile <YOUR_PROFILE>
```

**2. Delete Cognito User Pool**
```bash
# Delete the user pool
aws cognito-idp delete-user-pool \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --profile <YOUR_PROFILE>
```

**3. Delete AgentCore Runtime**
```bash
# List your agents to find the agent ID
aws bedrock-agentcore list-agent-runtimes \
  --profile <YOUR_PROFILE>

# Delete the agent
aws bedrock-agentcore delete-agent-runtime \
  --agent-id <YOUR_AGENT_ID> \
  --profile <YOUR_PROFILE>
```

**4. Delete Bedrock Guardrail (Optional)**
```bash
# List guardrails to find the ID
aws bedrock list-guardrails \
  --profile <YOUR_PROFILE>

# Delete the guardrail
aws bedrock delete-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --profile <YOUR_PROFILE>
```

**Finding Your Resource IDs (for CLI):**
- **User Pool ID**: Check the Lab 3 notebook outputs or run `aws cognito-idp list-user-pools --max-results 10`
- **Agent ID**: Check `.bedrock_agentcore.yaml` in the workshop directory or run `aws bedrock-agentcore list-agent-runtimes`
- **Guardrail ID**: Check notebook outputs or run `aws bedrock list-guardrails`

**CLI Documentation References:**
- 📖 [AWS CLI: admin-delete-user](https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/admin-delete-user.html)
- 📖 [AWS CLI: delete-user-pool](https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/delete-user-pool.html)
- 📖 [AWS CLI: bedrock-agentcore-control](https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/)
- 📖 [AWS API: DeleteGuardrail](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_DeleteGuardrail.html)

### Production Cleanup
```bash
cd production/

# Preview what will be deleted
uv run python cleanup.py --dry-run

# Complete cleanup
uv run python cleanup.py
```

**Note**: The production cleanup script automatically handles all resources including Cognito, AgentCore, ECR, IAM roles, and SSM parameters.

---

## 📚 Resources

- **Workshop Guide**: [workshop/README.md](./workshop/README.md)
- **Production Guide**: [production/README.md](./production/README.md)
- **Workshop Slides**: https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US
- **Strands Documentation**: https://strandsagents.com/latest/
- **AgentCore Docs**: https://docs.aws.amazon.com/bedrock-agentcore/
- **AgentCore Toolkit**: https://aws.github.io/bedrock-agentcore-starter-toolkit/

---

## 📄 License & Attribution

Apache License 2.0 - See [LICENSE](../LICENSE) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**Original Source**: https://github.com/awslabs/amazon-bedrock-agentcore-samples

This implementation demonstrates multi-agent financial advisory systems using AWS Bedrock AgentCore, adapted for educational purposes and enterprise deployments.
