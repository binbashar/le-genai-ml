# AWS Setup Guide

Complete AWS environment setup for the AgentCore workshop. Each participant needs their own AWS account.

---

## Prerequisites

Before starting this guide, you need:

- ✅ **Your own AWS account** (see [Step 1: Create AWS Account](#step-1-create-your-aws-account) below)
- ✅ **Email access** (for AWS account verification)
- ✅ **Credit card** (for AWS account setup - workshop uses free tier where possible)

---

## Step 1: Create Your AWS Account

**⚠️ Important**: Each workshop participant needs their **own individual AWS account**. Do not share accounts.

### Option A: New AWS Account (Recommended)

If you don't have an AWS account yet:

1. **Go to AWS Sign-Up**
   - Visit: https://portal.aws.amazon.com/billing/signup
   - Click **"Create a new AWS account"**

2. **Enter Account Information**
   - **Email address**: Use your personal or work email
   - **Password**: Create a strong password (save it securely!)
   - **AWS account name**: Choose a descriptive name (e.g., "MyName Workshop Account")

3. **Provide Contact Information**
   - Select **"Personal"** account type (unless using for business)
   - Fill in your name, phone number, and address
   - Accept the AWS Customer Agreement

4. **Add Payment Information**
   - Enter credit card details
   - **Note**: Most workshop resources are free tier eligible or very low cost (<$5)
   - You can set up billing alerts later (recommended)

5. **Verify Your Identity**
   - Choose phone verification method (SMS or voice call)
   - Enter the verification code sent to your phone

6. **Select Support Plan**
   - Choose **"Basic support - Free"**
   - You can upgrade later if needed

7. **Wait for Account Activation**
   - Account activation takes 5-10 minutes
   - You'll receive a confirmation email when ready
   - Sign in at: https://console.aws.amazon.com/

### Option B: Existing AWS Account

If you already have an AWS account:

1. **Ensure Administrator Access**
   - You need full administrative permissions for this workshop
   - Check by signing in to AWS Console: https://console.aws.amazon.com/
   - Try accessing services: IAM, Bedrock, ECR, CloudFormation

2. **Clean Existing Resources (Optional but Recommended)**
   - Consider using a clean account to avoid conflicts
   - Or ensure you understand existing resources in your account

### Step 1.1: Set Up Billing Alerts (Recommended)

Protect yourself from unexpected costs:

1. Sign in to AWS Console: https://console.aws.amazon.com/
2. Click your account name (top right) → **"Billing and Cost Management"**
3. In left menu, click **"Budgets"**
4. Click **"Create budget"**
5. Choose **"Zero spend budget"** (get alerted on any charges)
6. Or create a custom budget (e.g., $10/month)
7. Enter your email for alerts
8. Click **"Create budget"**

---

## Step 2: Install AWS CLI

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

## Step 3: Create Access Keys

You need AWS credentials to use the CLI:

1. **Sign in to AWS Console**
   - Go to: https://console.aws.amazon.com/

2. **Navigate to IAM**
   - Search for "IAM" in the top search bar
   - Click **"IAM"** service

3. **Create Access Key**
   - In left menu, click **"Users"**
   - Click your username (or create a new IAM user with Administrator access)
   - Click **"Security credentials"** tab
   - Scroll to **"Access keys"** section
   - Click **"Create access key"**

4. **Choose Use Case**
   - Select **"Command Line Interface (CLI)"**
   - Check the confirmation box
   - Click **"Next"**

5. **Add Description (Optional)**
   - Description tag: "Workshop CLI Access"
   - Click **"Create access key"**

6. **Save Your Credentials**
   - **⚠️ CRITICAL**: Save both keys immediately - you cannot retrieve the Secret Key later!
   - **Access Key ID**: AKIAIOSFODNN7EXAMPLE
   - **Secret Access Key**: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   - Click **"Download .csv file"** (backup)
   - Store securely (password manager recommended)

---

## Step 4: Configure AWS CLI

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

**Important**: Use **`us-west-2`** as your default region for this workshop.

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

## Step 5: Enable Bedrock Model Access

**As of October 2025**: Bedrock models are automatically enabled for new AWS accounts. This step is only needed for legacy accounts.

### For Legacy Accounts Only

If you have an older AWS account created before October 2025:

1. **Go to Bedrock Console**
   - Visit: https://console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess

2. **Enable Model Access**
   - Click **"Modify model access"** (if you see this option)
   - Enable these models:
     - ✅ **Amazon Nova** (all variants: Micro, Lite, Pro, Premier)
     - ✅ **Anthropic Claude 3.5** (Haiku, Sonnet)
     - ✅ **Anthropic Claude 4.5** (Haiku, Sonnet)

3. **Save Changes**
   - Click **"Save changes"**
   - Access is granted instantly (no approval needed)

### Verify Model Access

```bash
# List available models
aws bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `nova`) || contains(modelId, `claude`)].modelId' --output table

# You should see Nova and Claude models listed
```

---

## Step 6: Bootstrap AWS CDK

CDK needs to be bootstrapped once per account and region:

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

## Step 7: Verify Complete Setup

Run the automated validation script:

```bash
cd genai-agentcore-demos
./quickstart.sh
```

**Expected output**:
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

---

## Troubleshooting

### "Unable to locate credentials"

**Solution**:
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

### "Access Denied" for Bedrock

**Solution**:
1. Ensure you're using **Administrator** IAM permissions
2. For legacy accounts: Enable model access in Bedrock Console
3. Check your account doesn't have restrictive SCPs (Service Control Policies)

### "CDK Bootstrap Failed"

**Solution**:
```bash
# Ensure you have the correct account ID
aws sts get-caller-identity

# Try bootstrap with verbose output
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-west-2 --verbose

# Check CloudFormation console for error details
# https://console.aws.amazon.com/cloudformation/
```

### "Region Mismatch"

**Solution**:
```bash
# Ensure us-west-2 is your default region
aws configure get region
# Should output: us-west-2

# If not, set it:
aws configure set region us-west-2
```

---

## Cost Estimates

**Expected workshop costs** (assuming 2-hour session):

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| **Bedrock (Nova/Claude)** | ~50 requests | ~$0.10 - $0.50 |
| **AgentCore Runtime** | 2 hours active | ~$0.20 - $0.40 |
| **ECR Storage** | <1 GB for 1 day | ~$0.01 |
| **CloudWatch Logs** | <100 MB | ~$0.01 |
| **DynamoDB (Memory)** | Minimal reads/writes | ~$0.01 |
| **S3** | CodeBuild artifacts | ~$0.01 |

**Total**: **$0.34 - $0.94** for a 2-hour workshop

**Free Tier**: Some services (S3, ECR, CloudWatch, DynamoDB) have free tier allowances that may cover workshop usage.

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

3. **Use billing alerts**
   - Set up budget alerts (see Step 1.1)
   - Monitor AWS Cost Explorer

4. **Delete resources after workshop**
   - Run `cleanup.py` to remove all deployed resources
   - Check AWS Console for any remaining resources

---

## Next Steps

✅ Once all steps are complete, return to the main README and start the workshop:

```bash
cd genai-agentcore-demos
./quickstart.sh  # Validate everything is ready

# Start workshop
cd finance-personal-assistant/workshop
jupyter lab
```

Open `lab1-develop_a_personal_budget_assistant_strands_agent.ipynb` to begin!

---

## Additional Resources

- [AWS Account Creation Documentation](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html)
- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [AWS Free Tier Details](https://aws.amazon.com/free/)
