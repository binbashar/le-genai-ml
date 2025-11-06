# AWS Setup Guide for Workshop Participants

This guide helps you configure your AWS credentials for the AgentCore workshop. Each participant should use their own AWS profile.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option A: AWS SSO (Recommended)](#option-a-aws-sso-recommended)
3. [Option B: IAM User Credentials](#option-b-iam-user-credentials)
4. [Verify Your Configuration](#verify-your-configuration)
5. [Bootstrap AWS CDK](#bootstrap-aws-cdk)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- AWS account with administrative access (or permissions for Bedrock, IAM, AgentCore)
- AWS CLI v2 installed ([Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- Terminal/command line access

**Verify AWS CLI installation:**
```bash
aws --version
# Should show: aws-cli/2.x.x or higher
```

---

## Option A: AWS SSO (Recommended)

AWS Single Sign-On (SSO) is the recommended authentication method for organizations using AWS Organizations.

### Step 1: Configure SSO Profile

Run the interactive SSO configuration:

```bash
aws configure sso
```

You'll be prompted for the following information:

**1. SSO Session name (Recommended):**
```
SSO session name (Recommended): my-sso-session
```
Enter a memorable name for your SSO session (e.g., `workshop-session`, `company-sso`).

**2. SSO start URL:**
```
SSO start URL [None]: https://my-company.awsapps.com/start
```
This is provided by your AWS administrator. It typically looks like:
- `https://[your-domain].awsapps.com/start`
- `https://d-xxxxxxxxxx.awsapps.com/start`

**3. SSO Region:**
```
SSO region [None]: us-east-1
```
This is the region where your SSO directory is hosted (often `us-east-1`). Ask your AWS administrator if unsure.

**4. SSO registration scopes:**
```
SSO registration scopes [sso:account:access]:
```
Press Enter to accept the default (`sso:account:access`).

**5. Browser authentication:**

Your browser will open automatically to complete authentication:
- Sign in with your organization's credentials
- Grant AWS CLI access when prompted
- Return to your terminal

**6. Select AWS Account:**
```
There are N AWS account(s) available to you.
> Account-Name (123456789012)
```
Use arrow keys to select your workshop AWS account, then press Enter.

**7. Select IAM Role:**
```
Using the account ID 123456789012
There are N role(s) available to you.
> AdministratorAccess
  PowerUserAccess
```
Select the role with sufficient permissions (e.g., `AdministratorAccess`, `PowerUserAccess`).

**8. CLI default region:**
```
CLI default client Region [None]: us-west-2
```
Enter your preferred region. Recommended: `us-west-2` (where AgentCore is available).

**9. CLI default output format:**
```
CLI default output format [None]: json
```
Enter `json` (recommended for programmatic access).

**10. CLI profile name:**
```
CLI profile name [AdministratorAccess-123456789012]: workshop-profile
```
Enter a memorable name for your profile (e.g., `workshop`, `your-name`, `company-workshop`).

### Step 2: Login to SSO

Authenticate your SSO session:

```bash
aws sso login --profile workshop-profile
```

This will open your browser for authentication. Once complete, your credentials are cached.

### Step 3: Set Default Profile

Set your profile as the default for this terminal session:

```bash
export AWS_PROFILE=workshop-profile
```

**Make it persistent** (optional, add to your shell profile):

```bash
# For bash users
echo 'export AWS_PROFILE=workshop-profile' >> ~/.bashrc
source ~/.bashrc

# For zsh users (macOS default)
echo 'export AWS_PROFILE=workshop-profile' >> ~/.zshrc
source ~/.zshrc
```

### Step 4: Verify SSO Configuration

Test your SSO configuration:

```bash
# Should show your account details
aws sts get-caller-identity

# Should show: us-west-2 (or your configured region)
aws configure get region
```

**Expected output:**
```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

### SSO Session Management

**Check session status:**
```bash
# List cached SSO credentials
aws configure list

# View SSO session details
cat ~/.aws/config
```

**Renew expired session:**
```bash
# SSO sessions expire after 8 hours (default)
aws sso login --profile workshop-profile
```

**Logout:**
```bash
aws sso logout
```

---

## Option B: IAM User Credentials

If your organization doesn't use AWS SSO, configure IAM user credentials with access keys.

### Step 1: Obtain Access Keys

**From AWS Console:**
1. Sign in to AWS Console: https://console.aws.amazon.com/
2. Navigate to: **IAM → Users → [Your Username] → Security credentials**
3. Click "Create access key"
4. Select use case: "Command Line Interface (CLI)"
5. Add description tag (optional): "Workshop CLI Access"
6. Click "Create access key"
7. **Important:** Download the `.csv` file or copy the keys immediately (they won't be shown again)

You'll receive:
- **Access Key ID**: `AKIAIOSFODNN7EXAMPLE`
- **Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

### Step 2: Configure IAM Profile

Run the AWS CLI configuration:

```bash
aws configure --profile workshop-profile
```

Enter your credentials when prompted:

```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-west-2
Default output format [None]: json
```

### Step 3: Set Default Profile

```bash
export AWS_PROFILE=workshop-profile
```

**Make it persistent** (optional):

```bash
# For bash
echo 'export AWS_PROFILE=workshop-profile' >> ~/.bashrc
source ~/.bashrc

# For zsh (macOS)
echo 'export AWS_PROFILE=workshop-profile' >> ~/.zshrc
source ~/.zshrc
```

### Step 4: Verify IAM Configuration

```bash
# Should show your account details
aws sts get-caller-identity

# Should show: us-west-2
aws configure get region
```

### Security Best Practices for IAM Users

- ✅ Enable MFA (Multi-Factor Authentication) on your IAM user
- ✅ Rotate access keys regularly (every 90 days)
- ✅ Never commit access keys to Git repositories
- ✅ Use least-privilege permissions (only required permissions)
- ✅ Delete unused access keys

---

## Verify Your Configuration

Run these commands to ensure everything is configured correctly:

```bash
# 1. Check AWS CLI version
aws --version
# Expected: aws-cli/2.x.x or higher

# 2. Verify active profile
echo $AWS_PROFILE
# Expected: workshop-profile (or your chosen name)

# 3. Test credentials
aws sts get-caller-identity
# Expected: Your account ID, user ARN, and user ID

# 4. Check region
aws configure get region
# Expected: us-west-2 (or your configured region)

# 5. Test Bedrock access (optional)
aws bedrock list-foundation-models --region us-west-2 --max-results 1
# Expected: JSON response with model information
```

**All checks passed?** You're ready to proceed with the workshop!

---

## Bootstrap AWS CDK

Required once per AWS account and region (for deploying infrastructure with CDK):

```bash
# Using your configured profile
export AWS_PROFILE=workshop-profile

# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Bootstrap CDK (replace us-west-2 with your region if different)
cdk bootstrap aws://$ACCOUNT_ID/us-west-2
```

**Expected output:**
```
⏳  Bootstrapping environment aws://123456789012/us-west-2...
✅  Environment aws://123456789012/us-west-2 bootstrapped.
```

**Note:** You only need to bootstrap once per account/region combination.

---

## Troubleshooting

### Issue: "aws: command not found"

**Problem:** AWS CLI is not installed.

**Solution:**
1. Install AWS CLI v2: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
2. Verify installation: `aws --version`

---

### Issue: "Unable to locate credentials"

**Problem:** No AWS credentials configured or profile not found.

**Solution:**
```bash
# List configured profiles
aws configure list-profiles

# If no profiles exist, configure one:
aws configure sso  # For SSO
# OR
aws configure --profile workshop-profile  # For IAM user

# Set the profile
export AWS_PROFILE=workshop-profile
```

---

### Issue: "Error loading SSO Token: Token has expired"

**Problem:** SSO session expired (sessions expire after 8 hours by default).

**Solution:**
```bash
# Re-authenticate
aws sso login --profile workshop-profile
```

---

### Issue: "An error occurred (AccessDeniedException)"

**Problem:** Your IAM user/role lacks required permissions.

**Solution:**
1. Contact your AWS administrator
2. Request permissions for:
   - Bedrock model invocation (`bedrock:InvokeModel`)
   - AgentCore operations (`bedrock-agentcore:*`)
   - IAM role management (for deployment)
   - CloudWatch Logs (`logs:*`)
   - SSM Parameter Store (`ssm:GetParameter`, `ssm:PutParameter`)
3. Or request the managed policy: `BedrockAgentCoreFullAccess`

---

### Issue: "Region not configured"

**Problem:** Default region not set.

**Solution:**
```bash
# Set region for current profile
aws configure set region us-west-2 --profile workshop-profile

# Or export as environment variable
export AWS_REGION=us-west-2
```

---

### Issue: "Profile not found"

**Problem:** Typo in profile name or profile doesn't exist.

**Solution:**
```bash
# List all configured profiles
aws configure list-profiles

# View profile details
cat ~/.aws/config
cat ~/.aws/credentials  # For IAM users only

# Use correct profile name
export AWS_PROFILE=<exact-profile-name>
```

---

### Issue: CDK Bootstrap Fails

**Problem:** Insufficient permissions or region mismatch.

**Solution:**
```bash
# Verify you have permissions for:
# - CloudFormation
# - S3
# - IAM
# - ECR
# Contact AWS administrator if needed

# Ensure region matches
aws configure get region

# Try with explicit profile and region
cdk bootstrap aws://ACCOUNT_ID/us-west-2 --profile workshop-profile
```

---

## Quick Reference

### Essential Commands

```bash
# Configure SSO profile
aws configure sso

# Login to SSO
aws sso login --profile PROFILE_NAME

# Configure IAM user profile
aws configure --profile PROFILE_NAME

# Set active profile
export AWS_PROFILE=PROFILE_NAME

# Verify credentials
aws sts get-caller-identity

# Check region
aws configure get region

# List profiles
aws configure list-profiles

# View configuration
cat ~/.aws/config
```

### Configuration Files

- **`~/.aws/config`**: AWS profiles and SSO configuration
- **`~/.aws/credentials`**: IAM user access keys (for Option B only)
- **`~/.aws/sso/cache/`**: Cached SSO tokens

---

## Additional Resources

- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [AWS SSO Setup Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS CDK Bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)

---

## Need Help?

- **During workshop:** Ask your instructor or post in the workshop Slack/chat channel
- **AWS Support:** https://support.aws.amazon.com/
- **AWS Documentation:** https://docs.aws.amazon.com/

---

**Ready to proceed?** Return to the [main README](README.md) to continue with the workshop setup!
