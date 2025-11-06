# GenAI AgentCore Demos

Production-ready multi-agent financial advisory system demonstrating AWS Bedrock AgentCore. This workshop-ready codebase showcases specialized agents coordinating through intelligent orchestration.

## Prerequisites

### Workshop Requirements

This project is designed for AWS workshops. Participants need an **AWS account with administrator access** to deploy agents, configure IAM roles, and manage Bedrock resources.

---

### Operating System

Compatible with UNIX-like systems:
- **macOS** (Darwin)
- **Ubuntu/Debian Linux**
- **Windows Subsystem for Linux (WSL 2)**

**Note:** Native Windows users require WSL 2 for bash script execution.

---

### Required Tools

| Tool | Version | Installation |
|------|---------|-------------|
| **Python** | 3.13 | [python.org/downloads](https://www.python.org/downloads/) |
| **Node.js** | 25.0 or 22.21.0 LTS | [nodejs.org](https://nodejs.org/) |
| **AWS CLI** | v2 (latest) | [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| **AWS CDK** | v2 (latest) | `npm install -g aws-cdk` |
| **Docker** | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Git** | Latest | [git-scm.com/downloads](https://git-scm.com/downloads) |
| **uv** | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

#### Verification

```bash
python --version          # 3.13.x
node --version            # 25.x or 22.21.x
aws --version             # 2.x
cdk --version             # 2.x
docker --version          # Latest
git --version             # Any recent
uv --version              # Latest
```

---

### AWS Configuration

#### 1. Configure AWS SSO Profile

AWS SSO is recommended for seamless authentication across the demos:

```bash
# Configure SSO profile (interactive)
aws configure sso

# Login to SSO session
aws sso login --profile YOUR_PROFILE_NAME

# Verify credentials
aws sts get-caller-identity --profile YOUR_PROFILE_NAME
```

**Note:** The codebase uses a configurable AWS profile. Set your profile via `AWS_PROFILE` environment variable or update deployment scripts.

#### 2. Bootstrap AWS CDK

Required once per AWS account and region:

```bash
export AWS_PROFILE=YOUR_PROFILE_NAME
cdk bootstrap aws://ACCOUNT_ID/REGION
```

#### 3. Bedrock Model Access (October 2025 Update)

**No manual configuration needed.** As of October 2025, all Amazon Bedrock foundation models are automatically enabled by default. Administrator accounts have the necessary IAM permissions.

**Anthropic Models:** First-time users must submit a one-time use case form (instant approval):
- Select any Anthropic Claude model in the [Bedrock Console](https://console.aws.amazon.com/bedrock/)
- Complete the use case form when prompted
- Access granted immediately

**Required IAM Permissions:**
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `aws-marketplace:Subscribe` (auto-subscription on first model invocation)

Administrator accounts typically have these permissions by default.

---

## Next Steps

1. Clone the repository
2. Navigate to specific agent directories (`finance-personal-assistant/` or `market-trends-agent/`)
3. Follow agent-specific deployment guides in their READMEs
4. Run the Streamlit demo (`ui/`) to interact with deployed agents