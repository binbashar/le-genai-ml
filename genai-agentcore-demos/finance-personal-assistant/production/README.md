# Finance Personal Assistant - Production Deployment

**Production-ready multi-agent financial advisory system** with enterprise features.

## 🚀 Features

- **Multi-Agent Orchestration**: Specialized agents for budgeting and investment analysis
- **AgentCore Memory**: Multi-strategy context retrieval (USER_PREFERENCE, SEMANTIC, SUMMARY)
- **Vision Analysis**: Process receipts and invoices with Amazon Nova Premier
- **Document Processing**: CSV and PDF file parsing with security sanitization
- **OAuth2 Authentication**: Production-grade Cognito integration via CDK
- **Service Discovery**: SSM Parameter Store for dynamic configuration
- **Streaming Responses**: Real-time SSE streaming for responsive UX
- **Guardrails**: Content filtering and PII protection

---

## 📋 Prerequisites

**Run the automated validation script from project root:**

```bash
cd ../../  # Navigate to genai-agentcore-demos root
./quickstart.sh
```

This checks: AWS CLI, Python 3.13+, Docker, AWS CDK, uv, Bedrock model access, CDK bootstrap.

**Need help?** See [Pre-Workshop Checklist](../../PRE_WORKSHOP_CHECKLIST.md) for detailed configuration.

---

## 🎯 Quick Start

### Step 1: Install Dependencies

```bash
cd finance-personal-assistant/production
uv sync
```

---

### Step 2: Deploy to AWS

**Option A: With OAuth Authentication (Recommended)**

```bash
# Deploy Cognito infrastructure
cd cdk && ./deploy.sh && cd ..

# Configure and launch agent
./configure.sh  # Reads OAuth from SSM
./launch.sh     # Deploys to AWS, publishes ARN to SSM
```

**Option B: IAM Authentication Only**

```bash
./configure.sh  # Creates .bedrock_agentcore.yaml
./launch.sh     # Deploys to AWS
```

---

### Step 3: Verify Deployment

```bash
./health.sh                    # Cascading: AWS → Local
./health.sh --aws              # Test deployed agent only
./health.sh --timeout 120      # Custom timeout
```

---

### Step 4: Run the Streamlit Demo

```bash
# From project root
cd ../../ && ./demo.sh

# Or from ui directory
cd ../../ui && ./demo.sh
```

The UI auto-discovers deployed agents via SSM Parameter Store - no manual configuration needed!

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│  (Routes queries to appropriate specialist)                  │
└────────────────┬──────────────────────┬─────────────────────┘
                 │                      │
        ┌────────▼────────┐    ┌───────▼────────┐
        │  Budget Agent   │    │ Financial Agent │
        │                 │    │                 │
        │ • 50/30/20      │    │ • Stock Analysis│
        │ • Spending      │    │ • Portfolios    │
        │ • Health Score  │    │ • Comparisons   │
        └─────────────────┘    └─────────────────┘
                 │                      │
        ┌────────▼──────────────────────▼─────────┐
        │        AgentCore Memory                  │
        │  (Multi-strategy: USER_PREF, SEMANTIC)   │
        └──────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
production/
├── main.py                      # Orchestrator agent entrypoint
├── budget_agent.py              # Budget specialist
├── financial_analysis_agent.py  # Investment specialist
├── config.py                    # Model configuration
├── memory_config.py             # Memory strategies
├── test_vision.py               # Vision testing
├── deploy_guardrails.py         # Guardrails deployment
├── cleanup.py                   # Complete cleanup
├── reset_memory.py              # Memory reset
│
├── utils/
│   ├── vision_analyzer.py       # Nova Premier vision
│   ├── vision_context.py        # Vision context injection
│   ├── csv_processor.py         # CSV to text conversion
│   ├── pdf_processor.py         # PDF to image conversion
│   ├── session_manager.py       # Session/actor extraction
│   ├── memory_retrieval.py      # LTM retrieval
│   ├── guardrail.py             # Guardrails management
│   └── guardrail_sanitize.py    # Content sanitization
│
├── cdk/                         # Infrastructure as Code
│   ├── app.py                   # CDK app
│   ├── deploy.sh                # Deploy script
│   └── stacks/
│       ├── cognito_stack.py     # Cognito User Pool
│       └── execution_role_stack.py  # IAM role
│
├── configure.sh                 # Agent configuration
├── launch.sh                    # Agent deployment
├── health.py                    # Health checks
├── health.sh                    # Health wrapper
├── pyproject.toml               # Dependencies
├── Dockerfile                   # Container definition
└── .bedrock_agentcore.yaml      # Generated config
```

---

## 🔧 Development Workflow

### Local Testing

```bash
# Test budget agent locally
uv run python budget_agent.py

# Test financial analysis agent
uv run python financial_analysis_agent.py

# Test vision analysis
uv run python test_vision.py
```

### Iterative Deployment

```bash
# Make code changes to main.py, budget_agent.py, etc.

# Redeploy (creates new version, updates DEFAULT endpoint)
./launch.sh

# Test deployed version
./health.sh
```

### Deploy Guardrails

```bash
# Deploy guardrail for content filtering
uv run python deploy_guardrails.py

# Deploy with production version
uv run python deploy_guardrails.py --create-version
```

### Reset Memory

```bash
# Clear runtime-created memory (preserves configured STM)
uv run python reset_memory.py
```

### Complete Cleanup

```bash
# Preview what will be deleted
uv run python cleanup.py --dry-run

# Delete everything (Runtime, Memory, ECR, IAM)
uv run python cleanup.py

# Keep IAM roles
uv run python cleanup.py --skip-iam
```

---

## 🔐 Authentication Modes

### Option 1: OAuth2 with Cognito (Recommended)

```bash
# Deploy CDK infrastructure
cd cdk && ./deploy.sh && cd ..

# Configure agent (reads OAuth from SSM)
./configure.sh

# Launch agent
./launch.sh
```

### Option 2: IAM Authentication

```bash
# Configure without OAuth
./configure.sh

# Launch agent
./launch.sh
```

---

## 💾 Memory Configuration

The agent uses **three memory strategies**:

| Strategy | Purpose | Namespace | Top-K | Relevance |
|----------|---------|-----------|-------|-----------|
| **USER_PREFERENCE** | Name, goals, risk tolerance | `finance-assistant/user/{actorId}/preferences` | 5 | 0.7 |
| **SEMANTIC** | Budget amounts, spending patterns | `finance-assistant/user/{actorId}/facts` | 10 | 0.5 |
| **SUMMARY** | Conversation summaries | `finance-assistant/user/{actorId}/summaries/{sessionId}` | 3 | 0.6 |

**Memory retrieval** uses two patterns:
1. **Session Manager** (STM) - Automatic session context
2. **Direct Retrieval** (LTM) - Injected into prompt before invocation

---

## 🖼️ Vision & Document Support

### Supported Formats

- **Images**: JPEG, PNG (receipts, invoices, bank statements)
- **PDF**: First page converted to image for vision analysis
- **CSV**: Converted to text with formula injection prevention

### Usage

Send documents via API payload:
```json
{
  "prompt": "Analyze this receipt",
  "image_base64": "base64_encoded_image_data"
}
```

Or:
```json
{
  "prompt": "Extract data from this document",
  "document_base64": "base64_encoded_file",
  "filename": "statement.pdf"
}
```

---

## 🛡️ Guardrails

Content filtering includes:
- **Gambling content** (custom topic policy)
- **Sexual, violent, hateful content** (AWS managed)
- **PII protection** (email, phone, SSN redaction)
- **Prompt attack prevention**

**Automatic redaction** protects conversation history when guardrails trigger.

---

## 📊 Monitoring

### CloudWatch Logs

```bash
# View agent logs (replace {agent-id} from .bedrock_agentcore.yaml)
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

### Health Checks

```bash
# Cascading fallback (AWS → Local)
./health.sh

# Specific modes
./health.sh --aws              # Test deployed agent
./health.sh --local            # Test local HTTP endpoint
./health.sh --timeout 120      # Custom timeout
```

### Observability Dashboard

Visit the GenAI Observability Dashboard in AWS Console:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
```

---

## 🌐 Service Discovery

After deployment, the agent ARN is automatically published to SSM Parameter Store:

**Parameter**: `/agentcore/finance-personal-assistant/config`

**Structure**:
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

The Streamlit UI reads this automatically for agent discovery - no manual sync required!

---

## 🧪 Sample Queries

### Budget Queries
- "I make $6000/month. Help me create a budget."
- "I spend $800/month on dining out. Is this too much for my $5000 income?"
- "Generate a comprehensive financial report for someone earning $4000/month."

### Investment Queries
- "Analyze Apple stock and tell me if it's a good investment."
- "Create a moderate risk portfolio for $10,000."
- "Compare Tesla, Apple, and Google stocks over the last 6 months."

### Multi-Agent Queries
- "I make $5000/month and want to invest $1000. Help me budget and suggest a portfolio."
- "Analyze my $800 dining expenses, then recommend stocks to invest my savings."

### Vision Queries
- Upload receipt + "Track this expense in my budget."
- Upload invoice + "Add this to my monthly spending analysis."

---

## 🔄 Differences from Workshop

This production implementation adds:

| Feature | Workshop | Production |
|---------|----------|------------|
| **Memory** | STM only | Multi-strategy (3 strategies) |
| **Authentication** | Basic Cognito | CDK + OAuth2 |
| **Vision** | ❌ | ✅ Amazon Nova Premier |
| **Documents** | ❌ | ✅ CSV/PDF processing |
| **Deployment** | Manual | Scripted (configure.sh + launch.sh) |
| **Service Discovery** | Hardcoded ARNs | SSM Parameter Store |
| **Guardrails** | Basic | Production-grade with PII |
| **UI** | ❌ | ✅ Streamlit with SSE streaming |

---

## 📚 Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [AWS Bedrock AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Workshop Materials](../workshop/)

---

## 📄 License

Apache License 2.0 - See [LICENSE](../../LICENSE) for details.

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.
