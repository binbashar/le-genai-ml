# Pre-Workshop Checklist

Complete this checklist **before** starting the workshop to ensure a smooth experience.

## Prerequisites

### ☐ 1. AWS Account Setup

**Required:**
- AWS account with administrative access
- AWS CLI v2 installed and configured
- Valid AWS credentials

**Verify:**
```bash
# Check AWS CLI version (should be 2.x or higher)
aws --version

# Test credentials (should show your AWS account details)
AWS_PROFILE=binbash aws sts get-caller-identity

# Verify default region is set (recommended: us-west-2)
aws configure get region
```

**Expected output:**
```
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

---

### ☐ 2. Bedrock Model Access (October 2025 Update)

**No action required for new accounts.** As of October 2025, Amazon Bedrock automatically enables all serverless foundation models for every AWS account by default.

**What Changed:**
- All foundation models (Nova, Claude, etc.) are automatically accessible without manual setup
- The Model Access page and manual enablement process have been deprecated
- IAM policies and SCPs still control access as needed

**For Legacy AWS Accounts Only:**

If you're using an older AWS account that still requires manual model access enablement (uncommon), follow the legacy process:

**Steps:**
1. Go to: https://console.aws.amazon.com/bedrock/home#/modelaccess
2. Click "Modify model access" (if this option appears)
3. Enable the following models:
   - ✅ Amazon Nova Micro
   - ✅ Amazon Nova Lite
   - ✅ Amazon Nova Pro
   - ✅ Amazon Nova Premier (required for vision analysis)
   - ✅ Anthropic Claude 3.5 Haiku
   - ✅ Anthropic Claude 3.5 Sonnet
   - ✅ Anthropic Claude 4.5 Sonnet

**Note:** Access is granted instantly (no approval needed).

**Verify Model Access:**
```bash
# List available foundation models
aws bedrock list-foundation-models --region us-west-2 \
  --query 'modelSummaries[?contains(modelId, `nova`) || contains(modelId, `claude`)].modelId'
```

**Reference:** [AWS What's New - Amazon Bedrock simplifies access](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-automatic-enablement-serverless-foundation-models/)

---

### ☐ 3. Python Environment

**Required:**
- Python 3.13 or higher
- `uv` package manager

**Verify Python:**
```bash
# Check Python version (should be 3.13+)
python3 --version
```

**Install `uv` (if not installed):**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

---

### ☐ 4. Docker

**Required:** Docker Desktop or Docker Engine running

**Verify:**
```bash
# Check Docker version
docker --version

# Verify Docker is running (should list running containers)
docker ps
```

**Expected output:**
```
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

---

### ☐ 5. AWS CDK

**Required:** AWS CDK CLI for infrastructure deployment

**Install:**
```bash
npm install -g aws-cdk

# Verify installation
cdk --version
```

**Bootstrap CDK (one-time per account/region):**
```bash
AWS_PROFILE=binbash cdk bootstrap aws://ACCOUNT-ID/us-west-2
```

Replace `ACCOUNT-ID` with your AWS account number from step 1.

---

### ☐ 6. Repository Setup

**Clone and setup repository:**
```bash
# Clone repository
git clone <repository-url>
cd le-genai-ml/genai-agentcore-demos

# Install project dependencies
uv sync

# Verify installation
uv run python --version
```

---

### ☐ 7. AWS Permissions

**Required IAM permissions:**
- ✅ IAM role management (CreateRole, DeleteRole, GetRole, PutRolePolicy)
- ✅ Bedrock model invocation (bedrock:InvokeModel)
- ✅ AgentCore Runtime operations (bedrock-agentcore:*)
- ✅ ECR repository access (ecr:*)
- ✅ CodeBuild access (codebuild:*)
- ✅ CloudWatch Logs (logs:*)
- ✅ SSM Parameter Store (ssm:GetParameter, ssm:PutParameter)
- ✅ S3 (for build artifacts)

**Recommended:** Use `BedrockAgentCoreFullAccess` managed policy for workshop.

**Verify:**
```bash
# Test a simple Bedrock API call
aws bedrock list-foundation-models --region us-west-2 --max-results 1
```

---

### ☐ 8. Environment Variables

**Create `.env` file** (copy from example):
```bash
cd genai-agentcore-demos
cp .env.example .env
```

**Edit `.env` and set:**
```bash
AWS_PROFILE=binbash
AWS_REGION=us-west-2
```

---

## Quick Validation Script

Run this automated check:
```bash
cd genai-agentcore-demos
./quickstart.sh
```

This script will verify all prerequisites and report any issues.

---

## Troubleshooting

### Issue: AWS CLI not found
**Solution:** Install AWS CLI v2: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

### Issue: "Unable to locate credentials"
**Solution:** Configure AWS credentials:
```bash
aws configure --profile binbash
```

### Issue: Docker daemon not running
**Solution:** Start Docker Desktop or Docker service:
```bash
# macOS: Open Docker Desktop app
# Linux: sudo systemctl start docker
```

### Issue: Bedrock model access denied
**Solution:** This is rare for accounts created after October 2025. If you encounter this error:
1. Verify IAM permissions: `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`
2. For legacy accounts only: Enable model access in Bedrock Console (step 2 above)

### Issue: CDK not bootstrapped
**Solution:** Run CDK bootstrap command (step 5 above)

---

## Ready to Start?

Once all checkboxes are complete, you're ready to begin:

1. **Start with:** `workshop/lab1-develop_a_personal_budget_assistant_strands_agent.ipynb`
2. **Follow order:** Lab 1 → Lab 2 → Lab 3 → Streamlit Demo
3. **Estimated time:** 90-120 minutes total

**Need help?** Refer to `TROUBLESHOOTING.md` for common issues.

---

## Workshop Structure

```
Workshop Flow:
├── Lab 1: Develop Budget Assistant Agent (30 min)
│   └── Learn Strands framework basics
├── Lab 2: Build Multi-Agent Workflows (30 min)
│   └── Orchestrate multiple specialized agents
├── Lab 3: Deploy on Bedrock AgentCore (30 min)
│   └── Deploy to AWS with OAuth2 authentication
└── Streamlit Demo: Interactive UI (30 min)
    └── Test deployed agents with real-time streaming
```

Good luck! 🚀
