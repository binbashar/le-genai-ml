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

AWS SSO is the recommended method for authentication. Each workshop participant should use their own profile.

**Step 1: Configure SSO Profile**

```bash
# Interactive SSO configuration
aws configure sso

# You'll be prompted for:
# - SSO start URL (provided by your AWS administrator)
# - SSO Region (e.g., us-east-1)
# - Choose your AWS account and role
# - CLI default client Region (recommend: us-west-2)
# - CLI default output format (recommend: json)
# - CLI profile name (e.g., "workshop-profile" or your name)
```

**Step 2: Activate Your Profile**

```bash
# Set your profile as the default for this session
export AWS_PROFILE=your-profile-name

# Add to your shell profile (~/.bashrc, ~/.zshrc) for persistence:
echo 'export AWS_PROFILE=your-profile-name' >> ~/.bashrc  # or ~/.zshrc

# Login to SSO
aws sso login --profile your-profile-name

# Verify credentials
aws sts get-caller-identity
```

**Expected output:**
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

**Alternative: Using IAM User Credentials**

If you're not using SSO, configure IAM user credentials:

```bash
aws configure --profile your-profile-name
# Enter: AWS Access Key ID, Secret Access Key, Region, Output format

# Set as default
export AWS_PROFILE=your-profile-name
```

**Important:** Throughout this workshop, replace any reference to `AWS_PROFILE=binbash` with `AWS_PROFILE=your-profile-name` or simply use the exported environment variable.

📖 **Detailed Guide:** See [AWS_SETUP.md](./AWS_SETUP.md) for comprehensive AWS configuration instructions, including SSO setup, troubleshooting, and best practices.

#### 2. Bootstrap AWS CDK

Required once per AWS account and region:

```bash
# Using your configured profile
export AWS_PROFILE=your-profile-name
cdk bootstrap aws://ACCOUNT_ID/REGION

# Or specify profile inline
cdk bootstrap aws://ACCOUNT_ID/REGION --profile your-profile-name
```

Replace `ACCOUNT_ID` with your AWS account number (from `aws sts get-caller-identity`) and `REGION` with your target region (e.g., `us-west-2`).

#### 3. Bedrock Model Access (October 2025 Update)

**No manual configuration needed.** As of October 2025, Amazon Bedrock automatically enables all serverless foundation models for every AWS account by default. The previous manual "Model Access" enablement process has been deprecated.

**What Changed:**
- All serverless foundation models (Nova, Claude, etc.) are automatically accessible without setup
- The Model Access page in the Bedrock Console has been deprecated
- The `PutFoundationModelEntitlement` IAM permission has been retired
- IAM policies and Service Control Policies (SCPs) still control access if needed

**For Legacy Accounts:**
If you're using an older AWS account that still requires manual model access enablement, follow the legacy process:
1. Visit: https://console.aws.amazon.com/bedrock/home#/modelaccess
2. Click "Modify model access"
3. Enable required models: Amazon Nova (all variants), Anthropic Claude 3.5/4.5
4. Access is granted instantly

**Required IAM Permissions:**
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `aws-marketplace:Subscribe` (auto-subscription on first model invocation)

Administrator accounts typically have these permissions by default.

**Reference:** [AWS Security Blog - Simplified Model Access in Amazon Bedrock](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)

---

## Next Steps

1. Clone the repository
2. Navigate to specific agent directories (`finance-personal-assistant/` or `market-trends-agent/`)
3. Follow agent-specific deployment guides in their READMEs
4. Run the Streamlit demo (`ui/`) to interact with deployed agents