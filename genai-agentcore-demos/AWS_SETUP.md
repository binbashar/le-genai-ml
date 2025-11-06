# AWS Setup Guide for Workshop Participants

This guide helps you configure your AWS credentials for the AgentCore workshop. Each participant should use their own AWS profile.

## Table of Contents

1. [For Workshop Administrators: Creating IAM Users](#for-workshop-administrators-creating-iam-users)
2. [Prerequisites](#prerequisites)
3. [Configure IAM User Credentials (Recommended)](#configure-iam-user-credentials-recommended)
4. [Alternative: AWS SSO (For Organizations with Existing SSO)](#alternative-aws-sso-for-organizations-with-existing-sso)
5. [Verify Your Configuration](#verify-your-configuration)
6. [Bootstrap AWS CDK](#bootstrap-aws-cdk)
7. [Troubleshooting](#troubleshooting)

---

## For Workshop Administrators: Creating IAM Users

**Note:** This section is for AWS administrators preparing the environment for workshop participants. If you're a participant and have been provided credentials, skip to [Configure IAM User Credentials](#configure-iam-user-credentials-recommended).

### Why IAM Users for Workshops?

**IAM users are the recommended approach for workshops because:**
- ✅ **Fast setup**: 2 minutes per user (vs 30+ minutes for SSO infrastructure)
- ✅ **No dependencies**: Works without AWS Organizations or Identity Center
- ✅ **Reliable**: No authentication server dependencies during workshop
- ✅ **Simple cleanup**: Delete users after workshop
- ✅ **Works immediately**: Access keys ready to use right away

**Avoid AWS SSO for workshops unless:**
- Your organization already has IAM Identity Center fully configured
- All participants are already registered in your Identity Center
- You have tested SSO authentication with CLI beforehand

### Creating IAM Users for Workshop Participants

**Setup Instructions:**

```bash
# Create user (repeat for each participant)
aws iam create-user --user-name workshop-participant-1

# Attach administrator policy
aws iam attach-user-policy \
  --user-name workshop-participant-1 \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Create access key and save output
aws iam create-access-key --user-name workshop-participant-1
```

**Expected output:**
```json
{
    "AccessKey": {
        "UserName": "workshop-participant-1",
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "Status": "Active"
    }
}
```

**Important:** Save the Access Key ID and Secret Access Key securely - you'll share these with participants.

### Distributing Credentials to Participants

**Option 1: Secure file sharing (Recommended)**
1. Create a text file for each participant with their credentials
2. Share via secure channel (encrypted email, password-protected zip, 1Password, etc.)
3. Include instructions: See [Configure IAM User Credentials](#configure-iam-user-credentials-recommended)

**Option 2: In-person distribution**
1. Print credentials on paper (one per participant)
2. Hand out at start of workshop
3. Instruct participants to shred after adding to AWS CLI

**What to share with each participant:**
```
AWS Workshop Credentials - Participant 1

Access Key ID: AKIAIOSFODNN7EXAMPLE
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Region: us-west-2

Configuration command:
aws configure --profile workshop
(Enter the Access Key ID and Secret Access Key when prompted)
```

### Post-Workshop Cleanup

Delete IAM users after the workshop to maintain security:

```bash
# List access keys for user
aws iam list-access-keys --user-name workshop-participant-1

# Delete access key (use AccessKeyId from output above)
aws iam delete-access-key \
  --user-name workshop-participant-1 \
  --access-key-id AKIAIOSFODNN7EXAMPLE

# Detach policies
aws iam detach-user-policy \
  --user-name workshop-participant-1 \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Delete user
aws iam delete-user --user-name workshop-participant-1
```

**Batch cleanup script:**
```bash
#!/bin/bash
# cleanup-workshop-users.sh

for i in {1..10}; do
  USER="workshop-participant-$i"

  # Get and delete all access keys
  aws iam list-access-keys --user-name $USER --query 'AccessKeyMetadata[*].AccessKeyId' --output text | \
    xargs -I {} aws iam delete-access-key --user-name $USER --access-key-id {}

  # Detach policies
  aws iam detach-user-policy --user-name $USER --policy-arn arn:aws:iam::aws:policy/AdministratorAccess 2>/dev/null

  # Delete user
  aws iam delete-user --user-name $USER 2>/dev/null

  echo "Cleaned up: $USER"
done
```

### Alternative: AWS SSO (Only if Already Configured)

If your organization already has AWS IAM Identity Center (formerly AWS SSO) configured and all participants are registered, you may use SSO instead.

**⚠️ Warning:** Setting up SSO from scratch for a workshop is NOT recommended due to complexity and time requirements.

**For SSO setup instructions, see:**
- [IAM Identity Center Getting Started Guide](https://docs.aws.amazon.com/singlesignon/latest/userguide/getting-started.html)
- [Enable IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/get-set-up-for-idc.html)
- [AWS CLI SSO Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)

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

## Configure IAM User Credentials (Recommended)

IAM user credentials with access keys are the recommended authentication method for workshops. This method is fast, reliable, and works immediately without organizational dependencies.

**Your administrator should have provided you with:**
- AWS Access Key ID
- AWS Secret Access Key
- Region (typically: `us-west-2`)

### Step 1: Configure AWS CLI Profile

Run the AWS CLI configuration:

```bash
aws configure --profile workshop
```

Enter your credentials when prompted:

```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-west-2
Default output format [None]: json
```

**If you don't have access keys yet:**
Your workshop administrator should have provided them. If not, see the [For Workshop Administrators](#for-workshop-administrators-creating-iam-users) section above.

### Step 2: Set Default Profile

Set your profile as the default for this terminal session:

```bash
export AWS_PROFILE=workshop
```

**Make it persistent** (optional, add to your shell profile):

```bash
# For bash
echo 'export AWS_PROFILE=workshop' >> ~/.bashrc
source ~/.bashrc

# For zsh (macOS)
echo 'export AWS_PROFILE=workshop' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Verify Configuration

Test your configuration:

```bash
# Should show your account details
aws sts get-caller-identity

# Should show: us-west-2
aws configure get region
```

**Expected output:**
```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/workshop-participant-1"
}
```

### Security Best Practices

- ✅ Never commit access keys to Git repositories
- ✅ Delete keys after workshop (your administrator will handle this)
- ✅ Don't share your access keys with others
- ✅ Use the keys only for this workshop

---

## Alternative: AWS SSO (For Organizations with Existing SSO)

If your organization already has AWS IAM Identity Center (formerly AWS SSO) configured and you've been provided an SSO start URL, you can use SSO instead of IAM user credentials.

**⚠️ Important:** Do NOT attempt to set up SSO during the workshop. It requires organizational AWS setup and is too complex for workshop timeframes. Only use this option if:
- Your organization has IAM Identity Center already enabled
- You've been provided an SSO start URL by your administrator
- You've tested SSO authentication before the workshop

### Quick SSO Configuration

If you meet the requirements above:

```bash
# Run interactive SSO configuration
aws configure sso

# Follow the prompts:
# - SSO start URL: (provided by your administrator)
# - SSO Region: (typically us-east-1)
# - Select your AWS account and role
# - CLI default region: us-west-2
# - CLI profile name: workshop

# Login to SSO
aws sso login --profile workshop

# Set as default
export AWS_PROFILE=workshop

# Verify
aws sts get-caller-identity
```

### SSO Resources

For detailed SSO setup instructions, see official AWS documentation:
- [IAM Identity Center Getting Started](https://docs.aws.amazon.com/singlesignon/latest/userguide/getting-started.html)
- [AWS CLI SSO Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [SSO Session Management](https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html)

**Note:** If you encounter issues with SSO during the workshop, ask your administrator for IAM user credentials instead (recommended method above)

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
