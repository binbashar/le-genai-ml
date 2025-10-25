# AWS Profile Configuration Guide

The AgentCore demos now support flexible AWS profile configuration through environment variables.

## Quick Start

### Option 1: Set AWS Profile Name (If you have AWS CLI configured)

```bash
# Set your AWS SSO profile name
export AWS_PROFILE="your-sso-profile-name"

# Run health checks
cd /home/user/le-genai-ml/genai-agentcore-demos
python health.py
```

### Option 2: Export AWS Credentials Directly

If you have AWS credentials from SSO or temporary credentials:

```bash
# Export AWS credentials
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_SESSION_TOKEN="your-session-token"  # Required for SSO/temporary credentials
export AWS_REGION="us-west-2"  # Or your region

# Run health checks
cd /home/user/le-genai-ml/genai-agentcore-demos
python health.py
```

### Option 3: Create AWS Config File

Create `~/.aws/config` with your SSO profile:

```ini
[profile your-profile-name]
sso_start_url = https://your-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = YourRoleName
region = us-west-2
output = json
```

Then:

```bash
# Login via SSO
aws sso login --profile your-profile-name

# Set the profile
export AWS_PROFILE=your-profile-name

# Run health checks
cd /home/user/le-genai-ml/genai-agentcore-demos
python health.py
```

## What Changed

Both health check scripts now read from the `AWS_PROFILE` environment variable:

- **Market Trends Agent**: `genai-agentcore-demos/market-trends-agent/health.py`
- **Finance Personal Assistant**: `genai-agentcore-demos/finance-personal-assistant/health.py`

**Before:** Hardcoded to `aws_profile="binbash"`
**After:** `aws_profile = os.getenv("AWS_PROFILE", "binbash")`

## Testing Your Configuration

```bash
# Test if AWS credentials are working
cd /home/user/le-genai-ml/genai-agentcore-demos/market-trends-agent
uv run python -c "import boto3; print(boto3.client('sts').get_caller_identity())"

# Run full health check
cd /home/user/le-genai-ml/genai-agentcore-demos
python health.py
```

## Troubleshooting

### "No credentials found"
- Make sure `AWS_PROFILE` is exported: `echo $AWS_PROFILE`
- Or ensure AWS credentials are exported as environment variables
- Check if `~/.aws/config` exists and has your profile

### "Not deployed" error
- The health check looks for `.agent_arn` files in each agent directory
- If your agents are deployed, create these files with your ARNs:
  ```bash
  # Example:
  echo "arn:aws:bedrock-agentcore:us-west-2:123456789:runtime/your-agent" > market-trends-agent/.agent_arn
  echo "arn:aws:bedrock-agentcore:us-west-2:123456789:runtime/your-agent" > finance-personal-assistant/.agent_arn
  ```

### "Profile not found"
- List available profiles: `aws configure list-profiles` (requires AWS CLI)
- Or check `~/.aws/config` manually

## Running the Streamlit Demo

The Streamlit demo also respects AWS environment variables:

```bash
export AWS_PROFILE="your-sso-profile-name"
cd /home/user/le-genai-ml/genai-agentcore-demos/streamlit-demo
uv run streamlit run app.py
```

## Need Help?

If you're still having issues:
1. Check what profile boto3 sees: `uv run python -c "import boto3; print(boto3.Session().profile_name)"`
2. Verify credentials work: `uv run python -c "import boto3; print(boto3.client('sts').get_caller_identity())"`
3. Check the region: `uv run python -c "import boto3; print(boto3.Session().region_name)"`
