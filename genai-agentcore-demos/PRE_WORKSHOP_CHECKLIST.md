# Pre-Workshop Checklist

Complete this checklist **before** starting the workshop to ensure a smooth experience.

---

## Quick Navigation

**📌 Jump to Section:**
- [Prerequisites Overview](#prerequisites-overview) - Start here
- [Check Your Setup Status](#check-your-setup-status) - Run validation script first
- [AWS Account Setup](#1-aws-account-setup) - If you don't have an AWS account yet
- [Install AWS CLI](#2-install-aws-cli) - If AWS CLI not installed
- [Create Access Keys](#3-create-access-keys) - If you need AWS credentials
- [Configure AWS CLI](#4-configure-aws-cli) - Setup AWS credentials
- [Enable Bedrock Models](#5-enable-bedrock-model-access-legacy-accounts-only) - For older AWS accounts only
- [Bootstrap AWS CDK](#6-bootstrap-aws-cdk) - Required once per account/region
- [Python Environment](#7-python-environment) - Install Python and uv
- [Docker](#8-docker) - Install Docker
- [AWS CDK](#9-aws-cdk) - Install CDK CLI
- [Repository Setup](#10-repository-setup) - Clone and install dependencies
- [Troubleshooting](#troubleshooting) - If you encounter issues

---

## Prerequisites Overview

This workshop requires:
- ✅ **Your own AWS account** with administrative access
- ✅ **AWS CLI v2+** installed and configured
- ✅ **Python 3.13+** and `uv` package manager
- ✅ **Docker** running locally
- ✅ **AWS CDK** bootstrapped in us-west-2

**💰 Workshop Cost:** Less than $1 per session

**Conditional Navigation:**
- ✅ Already have AWS account configured? → Skip to [Python Environment](#7-python-environment)
- ✅ Already have Python, Docker, CDK installed? → Skip to [Repository Setup](#10-repository-setup)
- ✅ Setup completed previously? → Go to [Check Your Setup Status](#check-your-setup-status)

---

## Check Your Setup Status

**👉 Run this validation script to check where you are in the setup process:**

```bash
cd genai-agentcore-demos
./quickstart.sh
```

**Note:** The script already has execution permissions when cloned from git. If you encounter a "Permission denied" error (rare), run: `chmod +x quickstart.sh`

This automated script checks all prerequisites and shows you exactly what's configured and what still needs setup.

**Expected output:**
```
✓ AWS CLI v2.x.x installed
✓ AWS credentials valid (Account: 123456789012)
✓ Default region set: us-west-2
✓ Bedrock model access enabled (8 Nova, 30 Claude models)
✓ Amazon Nova Premier (required for vision) - Available
✓ Python 3.13.x installed
✓ uv vx.x.x installed
✓ Docker vx.x.x installed
✓ Docker daemon is running
✓ AWS CDK vx.x.x installed
✓ CDK bootstrapped in us-west-2
✓ In correct directory (genai-agentcore-demos)
✓ Virtual environment exists (.venv)
✓ Bedrock API access verified
✓ ECR access verified

===================================================
Validation Summary
===================================================

Passed:   16
Warnings: 0
Failed:   0

✓ All checks passed! You're ready to start the workshop.
```

**What to do if checks fail:**

- ❌ **AWS CLI not installed?** → Go to [Install AWS CLI](#2-install-aws-cli)
- ❌ **AWS credentials not valid?** → Go to [Create Access Keys](#3-create-access-keys) and [Configure AWS CLI](#4-configure-aws-cli)
- ❌ **Python/Docker/CDK missing?** → Follow the relevant sections below
- ❌ **CDK not bootstrapped?** → Go to [Bootstrap AWS CDK](#6-bootstrap-aws-cdk)
- ❌ **Bedrock model access denied?** → Go to [Enable Bedrock Models](#5-enable-bedrock-model-access-legacy-accounts-only)

**Note:** You can run `./quickstart.sh` at any time to check your progress!

---

## 1. AWS Account Setup

**⚠️ Important:** Each workshop participant needs their **own individual AWS account**. Do not share accounts.

**Why individual accounts?**
- **Isolation:** Your deployments won't interfere with others
- **Cost Control:** Track exactly what your experiments cost
- **Learning Independence:** Hands-on experience with full AWS setup
- **Security:** No risk of accessing/modifying others' resources

**Already have an AWS account?** → Skip to [Install AWS CLI](#2-install-aws-cli)

---

### Option A: New AWS Account (Recommended)

If you don't have an AWS account yet:

**Step 1: Go to AWS Sign-Up**
- Visit: https://portal.aws.amazon.com/billing/signup
- Click **"Create a new AWS account"**

**Step 2: Enter Account Information**
- **Email address:** Use your personal or work email
- **Password:** Create a strong password (save it securely!)
- **AWS account name:** Choose a descriptive name (e.g., "MyName Workshop Account")

**Step 3: Provide Contact Information**
- Select **"Personal"** account type (unless using for business)
- Fill in your name, phone number, and address
- Accept the AWS Customer Agreement

**Step 4: Add Payment Information**
- Enter credit card details
- **Note:** Most workshop resources are free tier eligible or very low cost (<$1!! 🔥)

**Step 5: Verify Your Identity**
- Choose phone verification method (SMS or voice call)
- Enter the verification code sent to your phone

**Step 6: Select Support Plan**
- Choose **"Basic support - Free"**
- You can upgrade later if needed

**Step 7: Wait for Account Activation**
- You'll receive a confirmation email when ready
- Sign in at: https://console.aws.amazon.com/

---

### Option B: Existing AWS Account

If you already have an AWS account:

**1. Ensure Administrator Access**
- You need full administrative permissions for this workshop
- Check by signing in to AWS Console: https://console.aws.amazon.com/
- Try accessing services: IAM, Bedrock, ECR, CloudFormation

**2. Clean Existing Resources (Optional but Recommended)**
- Consider using a clean account to avoid conflicts
- Or ensure you understand existing resources in your account

---

## 2. Install AWS CLI

**What is the AWS CLI?** The AWS Command Line Interface (CLI) is a unified tool to manage your AWS services from the terminal. Instead of clicking through the AWS Console web interface, you can automate tasks with scripts and commands.

**Why AWS CLI v2+?**
- **Performance:** 2-3x faster startup time compared to v1
- **Better installer:** Easier to install and update on all platforms
- **Modern features:** Support for SSO, improved output formatting, better error messages
- **Active development:** v1 is no longer actively maintained

**Already have AWS CLI installed?** → Verify with `aws --version` (should be 2.x), then skip to [Create Access Keys](#3-create-access-keys)

---

### macOS

```bash
# Download installer
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"

# Install
sudo installer -pkg AWSCLIV2.pkg -target /

# Verify
aws --version
# Expected: aws-cli/2.x.x
```

### Linux

```bash
# Download and install
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
# Expected: aws-cli/2.x.x
```

### Windows (WSL 2)

```bash
# Inside WSL terminal
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
# Expected: aws-cli/2.x.x
```

---

## 3. Create Access Keys

**What are Access Keys?** AWS access keys are long-term credentials that authenticate your CLI commands. They consist of two parts:
- **Access Key ID:** Public identifier (like a username)
- **Secret Access Key:** Private credential (like a password) - never share this!

**Why Access Keys instead of AWS SSO?** For workshops, access keys provide:
- **Simplicity:** No complex organization setup required
- **Independence:** Works with personal AWS accounts
- **Reliability:** No session timeouts during the workshop
- **Learning value:** Understanding IAM credentials is fundamental to AWS security

**Already have access keys?** → Skip to [Configure AWS CLI](#4-configure-aws-cli)

---

### Steps to Create Access Keys

**1. Sign in to AWS Console**
- Go to: https://console.aws.amazon.com/

**2. Navigate to IAM**
- Search for "IAM" in the top search bar
- Click **"IAM"** service

**3. Create Access Key**
- In left menu, click **"Users"**
- Click your username (or create a new IAM user with Administrator access)
- Click **"Security credentials"** tab
- Scroll to **"Access keys"** section
- Click **"Create access key"**

**4. Choose Use Case**
- Select **"Command Line Interface (CLI)"**
- Check the confirmation box
- Click **"Next"**

**5. Add Description (Optional)**
- Description tag: "Workshop CLI Access"
- Click **"Create access key"**

**6. Save Your Credentials**
- **⚠️ CRITICAL:** Save both keys immediately - you cannot retrieve the Secret Key later!
- **Access Key ID:** AKIAIOSFODNN7EXAMPLE
- **Secret Access Key:** wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
- Click **"Download .csv file"** (backup)
- Store securely

---

## 4. Configure AWS CLI

Configure your AWS credentials:

```bash
# Configure with your credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID [None]: PASTE_YOUR_ACCESS_KEY_ID
# AWS Secret Access Key [None]: PASTE_YOUR_SECRET_ACCESS_KEY
# Default region name [None]: us-west-2
# Default output format [None]: json
```

**Important:** Use **`us-west-2`** (US West Oregon) as your default region for this workshop.

**Why us-west-2?**
- **Geographic proximity:** Closest AWS region to San Francisco, minimizing latency
- **Full service availability:** Complete support for Amazon Bedrock, AgentCore Runtime, Nova models, and all Claude models
- **Cost efficiency:** Lower data transfer costs when all resources are in the same region
- **Consistency:** Everyone using the same region simplifies troubleshooting

### Verify Configuration

```bash
# Test your credentials
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

If you see your account ID and ARN, you're configured correctly! ✅

---

## 5. Enable Bedrock Model Access (Legacy Accounts Only)

👉 **As of October 2025:** Bedrock models are automatically enabled for new AWS accounts. This step is only needed for legacy accounts. 👈

**For New Accounts (created after October 2025):** → Skip to [Bootstrap AWS CDK](#6-bootstrap-aws-cdk)

---

### For Legacy Accounts Only

If you have an older AWS account created before October 2025:

**1. Go to Bedrock Console**
- Visit: https://console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess
- If you don't see the "Modify model access" option, you're all set!

**2. Enable Model Access**
- Click **"Modify model access"** (if you see this option)
- Enable these models:
  - ✅ **Amazon Nova** (all variants: Micro, Lite, Pro, Premier)
  - ✅ **Anthropic Claude 3.5** (Haiku, Sonnet)
  - ✅ **Anthropic Claude 4.5** (Haiku, Sonnet)

**3. Save Changes**
- Click **"Save changes"**
- Access is granted instantly (no approval needed)

### Verify Model Access

```bash
# List available models
aws bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `nova`) || contains(modelId, `claude`)].modelId' --output table

# You should see Nova and Claude models listed
```

---

## 6. Bootstrap AWS CDK

**What is CDK Bootstrapping?** The AWS Cloud Development Kit (CDK) uses Infrastructure as Code to define AWS resources. Before you can deploy CDK applications, AWS needs to prepare your environment with supporting resources.

**What does bootstrapping create?**
- **S3 Bucket:** Stores CDK synthesized templates and file assets (like Lambda code)
- **ECR Repository:** Stores Docker container images for containerized applications
- **IAM Roles:** Grants CDK the permissions needed to deploy resources on your behalf
- **CloudFormation Stack:** Named `CDKToolkit`, manages all bootstrap resources

**Why only once per region?** Bootstrap resources are shared across all CDK applications in that account/region, so you only need to set this up once.

**Already bootstrapped?** → Verify with `aws cloudformation describe-stacks --stack-name CDKToolkit --region us-west-2`, then skip to [Python Environment](#7-python-environment)

---

### Bootstrap CDK

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Bootstrap CDK in us-west-2
cdk bootstrap aws://$ACCOUNT_ID/us-west-2

# Expected output:
# ✅ Bootstrapping environment aws://123456789012/us-west-2...
# ✅ Environment aws://123456789012/us-west-2 bootstrapped
```

This creates a CloudFormation stack called `CDKToolkit` with resources needed for CDK deployments.

---

## 7. Python Environment

**Required:**
- Python 3.13 or higher
- `uv` package manager

**Already have Python 3.13+ and uv?** → Skip to [Docker](#8-docker)

---

### Install Python

**Verify Python version:**
```bash
# Check Python version (should be 3.13+)
python3 --version
```

**If you need to install Python 3.13:**
- **macOS:** `brew install python@3.13`
- **Linux:** Use your distribution's package manager or download from python.org
- **Windows (WSL):** `sudo apt install python3.13`

---

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

---

## 8. Docker

**Required:** Docker Desktop or Docker Engine running

**Already have Docker?** → Verify with `docker ps`, then skip to [AWS CDK](#9-aws-cdk)

---

### Install Docker

Download and install Docker Desktop:
- **macOS:** https://docs.docker.com/desktop/install/mac-install/
- **Linux:** https://docs.docker.com/desktop/install/linux-install/
- **Windows (WSL 2):** https://docs.docker.com/desktop/install/windows-install/

### Verify Docker

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

## 9. AWS CDK

**Required:** AWS CDK CLI for infrastructure deployment

**Already have CDK?** → Verify with `cdk --version`, then skip to [Repository Setup](#10-repository-setup)

---

### Install CDK

```bash
npm install -g aws-cdk

# Verify installation
cdk --version
```

---

## 10. Repository Setup

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

**Important for workshop participants:**
When working with the Jupyter notebooks, make sure to open your code editor (VS Code or Cursor) from the `genai-agentcore-demos/` directory. This folder contains the virtual environment (`.venv`) that your editor needs to detect the correct Python kernel for notebooks. Opening subdirectories will prevent proper kernel detection.

---

## Troubleshooting

### "Unable to locate credentials"

**Solution:**
```bash
# Re-configure AWS CLI
aws configure

# Verify credentials file exists
cat ~/.aws/credentials

# Should show:
# [default]
# aws_access_key_id = YOUR_ACCESS_KEY
# aws_secret_access_key = YOUR_SECRET_KEY
```

---

### "Access Denied" for Bedrock

**Solution:**
1. Ensure you're using **Administrator** IAM permissions
2. For legacy accounts: Enable model access in Bedrock Console (see [section](#5-enable-bedrock-model-access-legacy-accounts-only))
3. Check your account doesn't have restrictive SCPs (Service Control Policies)

---

### "CDK Bootstrap Failed"

**Solution:**
```bash
# Ensure you have the correct account ID
aws sts get-caller-identity

# Try bootstrap with verbose output
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-west-2 --verbose

# Check CloudFormation console for error details
# https://console.aws.amazon.com/cloudformation/
```

---

### "Region Mismatch"

**Solution:**
```bash
# Ensure us-west-2 is your default region
aws configure get region
# Should output: us-west-2

# If not, set it:
aws configure set region us-west-2
```

---

### Docker daemon not running

**Solution:**
```bash
# macOS: Open Docker Desktop app
# Linux: sudo systemctl start docker
```

---

### Issue: Bedrock model access denied

**Solution:** This is rare for accounts created after October 2025. If you encounter this error:
1. Verify IAM permissions: `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`
2. For legacy accounts only: Enable model access in Bedrock Console (see [section](#5-enable-bedrock-model-access-legacy-accounts-only))

---

## Cost Estimates

**Expected workshop costs:**

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| **Bedrock (Nova/Claude)** | ~50 requests | ~$0.10 - $0.20 |
| **AgentCore Runtime** | Active session | ~$0.10 - $0.20 |
| **ECR Storage** | <1 GB for 1 day | ~$0.01 |
| **CloudWatch Logs** | <100 MB | ~$0.01 |
| **DynamoDB (Memory)** | Minimal reads/writes | ~$0.01 |
| **S3** | CodeBuild artifacts | ~$0.01 |

**Total:** **Less than $1** per workshop session

**Free Tier:** Some services (S3, ECR, CloudWatch, DynamoDB) have free tier allowances that may cover workshop usage. 😎

### Cleanup After Workshop

To minimize costs after the workshop:

```bash
cd genai-agentcore-demos/finance-personal-assistant/production

# Complete cleanup (removes all deployed resources)
uv run cleanup.py

# Verify cleanup
aws bedrock-agentcore list-agent-runtimes --region us-west-2
# Should show empty list
```

---

## Security Best Practices

1. **Never commit credentials to Git**
   - AWS credentials are in `~/.aws/credentials` (not in repo)
   - `.gitignore` already excludes credential files

2. **Rotate access keys regularly**
   - After workshop, consider creating new access keys
   - Delete old access keys in IAM Console

3. **Delete resources after workshop**
   - Run `cleanup.py` to remove all deployed resources
   - Check AWS Console for any remaining resources

---

## Ready to Start?

Once all checks pass, you're ready to begin:

1. **Start with:** `workshop/lab1-develop_a_personal_budget_assistant_strands_agent.ipynb`
2. **Follow order:** Lab 1 → Lab 2 → Lab 3 → Streamlit Demo

**Need help?** Refer to the Troubleshooting section above.

---

## Workshop Structure

```
Workshop Flow:
├── Lab 1: Develop Budget Assistant Agent
│   └── Learn Strands framework basics
├── Lab 2: Build Multi-Agent Workflows
│   └── Orchestrate multiple specialized agents
├── Lab 3: Deploy on Bedrock AgentCore
│   └── Deploy to AWS with OAuth2 authentication
└── Streamlit Demo: Interactive UI
    └── Test deployed agents with real-time streaming
```

Good luck! 🚀

---

## Additional Resources

- [AWS Account Creation Documentation](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html)
- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [AWS Free Tier Details](https://aws.amazon.com/free/)
