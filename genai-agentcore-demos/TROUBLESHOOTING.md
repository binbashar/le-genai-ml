# Troubleshooting Guide

Common issues and solutions for GenAI AgentCore Demos.

---

## Quick Diagnostics

**🚀 Run the automated validation script first:**

```bash
./quickstart.sh
```

This will automatically check all prerequisites and identify most common setup issues.

---

## Table of Contents

1. [AWS Credentials & Authentication](#aws-credentials--authentication)
2. [Bedrock Model Access](#bedrock-model-access)
3. [AgentCore Deployment](#agentcore-deployment)
4. [Docker Issues](#docker-issues)
5. [Python & Dependencies](#python--dependencies)
6. [CDK Infrastructure](#cdk-infrastructure)
7. [Agent Runtime Issues](#agent-runtime-issues)
8. [Streamlit UI Issues](#streamlit-ui-issues)
9. [Memory & Session Issues](#memory--session-issues)
10. [OAuth/Cognito Issues](#oauthcognito-issues)

---

## AWS Credentials & Authentication

### Error: "Unable to locate credentials"

**Symptom:**
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution:**
```bash
# Configure AWS credentials
aws configure --profile binbash

# Or set environment variables
export AWS_PROFILE=binbash
export AWS_DEFAULT_REGION=us-west-2

# Verify credentials
AWS_PROFILE=binbash aws sts get-caller-identity
```

---

### Error: "The security token included in the request is expired"

**Symptom:**
```
An error occurred (ExpiredToken) when calling the XXX operation
```

**Solution:**
```bash
# If using SSO, re-authenticate
AWS_PROFILE=binbash aws sso login

# If using access keys, generate new credentials
aws configure --profile binbash
```

---

### Error: "Access Denied" for specific operations

**Symptom:**
```
An error occurred (AccessDenied) when calling the XXX operation
```

**Solution:**
This workshop requires **Administrator access** to your AWS account. Contact your AWS account administrator to grant you the `AdministratorAccess` managed policy.

**Why Administrator access?**
The workshop involves:
- Creating IAM roles and policies (CDK deployment)
- Building and pushing Docker images to ECR
- Deploying AgentCore Runtime instances
- Creating Cognito User Pools and App Clients
- Managing SSM parameters, CloudWatch Logs, S3 buckets

**Verify your access:**
```bash
# Test administrative permissions
aws iam list-roles --max-items 1
aws ecr describe-repositories --max-results 1
aws bedrock list-foundation-models --max-results 1
```

**Note:** The **AgentCore agents** themselves run with least-privilege execution roles that are automatically created by the CDK stack and AgentCore CLI.

---

## Bedrock Model Access

### Error: "Access denied to model"

**Symptom:**
```
AccessDeniedException: Your account is not authorized to invoke this model
```

**Solution:**
1. Go to: https://console.aws.amazon.com/bedrock/home#/modelaccess
2. Click "Modify model access"
3. Enable required models:
   - Amazon Nova (all variants)
   - Anthropic Claude 3.5/4.5 (Haiku, Sonnet)
4. Save changes (access is instant)

**Verify:**
```bash
AWS_PROFILE=binbash aws bedrock list-foundation-models \
  --region us-west-2 \
  --query 'modelSummaries[?contains(modelId, `nova`) || contains(modelId, `claude`)].modelId'
```

---

### Error: "ThrottlingException" or "Rate exceeded"

**Symptom:**
```
ThrottlingException: Rate exceeded for model XXX
```

**Solution:**
- Nova/Claude models have default quotas (requests/minute)
- Use inference profiles (us.amazon.nova-*, us.anthropic.claude-*) for cross-region routing
- Request quota increase: https://console.aws.amazon.com/servicequotas/

**Temporary workaround:**
Add retry logic or reduce concurrent requests.

---

## AgentCore Deployment

### Error: "agentcore: command not found"

**Symptom:**
```bash
./launch.sh
# Output: agentcore: command not found
```

**Solution:**
```bash
# Install dependencies first
uv sync

# Run with uv prefix
uv run agentcore launch

# Or activate virtual environment
source .venv/bin/activate
agentcore launch
```

---

### Error: "No such file or directory: .bedrock_agentcore.yaml"

**Symptom:**
```
FileNotFoundError: .bedrock_agentcore.yaml not found
```

**Solution:**
Run configuration first:
```bash
cd finance-personal-assistant/production
./configure.sh

# Or manually
uv run agentcore configure -e main.py
```

---

### Error: Docker build fails during deployment

**Symptom:**
```
Error: Docker build failed
Failed to create agent runtime
```

**Solution 1: Check Docker is running**
```bash
docker ps
# If fails, start Docker Desktop or daemon
```

**Solution 2: Check Docker Hub rate limits**
```bash
# Login to Docker Hub if using public images frequently
docker login
```

**Solution 3: Clean Docker cache**
```bash
docker system prune -af
docker builder prune -af
```

---

### Error: "ECR repository not accessible"

**Symptom:**
```
Error pulling image from ECR: AccessDenied
```

**Solution:**
```bash
# Authenticate Docker to ECR
AWS_PROFILE=binbash aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-west-2.amazonaws.com
```

---

### Error: CodeBuild timeout during deployment

**Symptom:**
```
CodeBuild project timed out after 60 minutes
```

**Solution:**
- Large Docker images can take time to build
- Check CodeBuild logs in AWS Console: https://console.aws.amazon.com/codesuite/codebuild/projects
- Optimize Dockerfile (use multi-stage builds, cache layers)

---

## Docker Issues

### Error: "Cannot connect to the Docker daemon"

**Symptom:**
```
Error: Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution:**
```bash
# macOS: Start Docker Desktop
open -a Docker

# Linux: Start Docker service
sudo systemctl start docker

# Verify
docker ps
```

---

### Error: "Docker build runs out of space"

**Symptom:**
```
no space left on device
```

**Solution:**
```bash
# Clean up Docker resources
docker system prune -af
docker volume prune -f

# Check disk space
df -h
```

---

## Python & Dependencies

### Error: "uv: command not found"

**Symptom:**
```bash
./launch.sh
# Output: uv: command not found
```

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell
source ~/.bashrc  # or ~/.zshrc

# Verify
uv --version
```

---

### Error: "No module named 'bedrock_agentcore'"

**Symptom:**
```python
ModuleNotFoundError: No module named 'bedrock_agentcore'
```

**Solution:**
```bash
# Install dependencies
cd finance-personal-assistant/production
uv sync

# Verify installation
uv run python -c "import bedrock_agentcore; print(bedrock_agentcore.__version__)"
```

---

### Error: Python version mismatch

**Symptom:**
```
This project requires Python 3.13 or higher
```

**Solution:**
```bash
# Check Python version
python3 --version

# Install Python 3.13+ if needed
# macOS (Homebrew):
brew install python@3.13

# Update .python-version
echo "3.13" > .python-version

# Re-sync dependencies
uv sync
```

---

## CDK Infrastructure

### Error: "CDK not bootstrapped"

**Symptom:**
```
Error: This stack uses assets, so the toolkit stack must be deployed
```

**Solution:**
```bash
# Bootstrap CDK in your account/region
AWS_PROFILE=binbash cdk bootstrap aws://ACCOUNT-ID/us-west-2

# Replace ACCOUNT-ID with your AWS account number
# Get account ID: aws sts get-caller-identity --query Account --output text
```

---

### Error: CDK deployment fails with "Rollback"

**Symptom:**
```
Stack finance-personal-assistant-cognito failed: Rollback complete
```

**Solution:**
```bash
# Check CloudFormation events for specific error
AWS_PROFILE=binbash aws cloudformation describe-stack-events \
  --stack-name finance-personal-assistant-cognito \
  --region us-west-2 \
  --max-items 10

# Common issues:
# - IAM permission denied → Add IAM permissions
# - Resource limit exceeded → Request quota increase
# - Resource name conflict → Delete old resources
```

---

### Error: "User pool with name already exists"

**Symptom:**
```
UserPoolAlreadyExists: User pool with name finance-personal-assistant already exists
```

**Solution:**
```bash
# Option 1: Delete existing Cognito User Pool (if safe to do so)
AWS_PROFILE=binbash aws cognito-idp list-user-pools --max-results 10
# Note the pool ID, then:
AWS_PROFILE=binbash aws cognito-idp delete-user-pool --user-pool-id POOL_ID

# Option 2: Change agent name in configuration
# Edit: finance-personal-assistant/production/.bedrock_agentcore.yaml
# Change: agent_name: "finance-personal-assistant-v2"
```

---

## Agent Runtime Issues

### Error: "Agent invocation timeout"

**Symptom:**
```
TimeoutError: Agent invocation exceeded 60 seconds
```

**Solution 1: Increase timeout**
```bash
# In health checks
./health.sh --timeout 120

# In Python code
response = client.invoke_agent(
    agentRuntimeArn=agent_arn,
    sessionId=session_id,
    input={"text": prompt},
    timeout=120  # seconds
)
```

**Solution 2: Check agent logs**
```bash
# Get agent ID from .bedrock_agentcore.yaml
AWS_PROFILE=binbash aws logs tail /aws/bedrock-agentcore/runtimes/AGENT-ID-DEFAULT --follow
```

---

### Error: "Health check fails in AWS mode"

**Symptom:**
```bash
./health.sh --aws
# Output: ✗ Health check failed in AWS mode
```

**Solution:**
```bash
# 1. Verify agent is deployed
uv run agentcore status

# 2. Check agent ARN in .bedrock_agentcore.yaml
cat .bedrock_agentcore.yaml | grep agent_arn

# 3. Test with AWS CLI directly
AWS_PROFILE=binbash aws bedrock-agentcore invoke-agent \
  --agent-runtime-arn "arn:aws:bedrock-agentcore:..." \
  --session-id "test-$(date +%s)" \
  --input '{"text":"Hello"}'

# 4. Check CloudWatch Logs for errors
```

---

### Error: "Memory retrieval failed"

**Symptom:**
```
MemoryRetrievalError: Failed to retrieve context from memory
```

**Solution:**
```bash
# Check if AgentCore Memory exists
AWS_PROFILE=binbash aws bedrock-agentcore list-memories --region us-west-2

# Verify memory ID in .bedrock_agentcore.yaml
grep memory_id .bedrock_agentcore.yaml

# Check memory permissions in IAM execution role
AWS_PROFILE=binbash aws iam get-role-policy \
  --role-name YOUR-EXECUTION-ROLE \
  --policy-name BedrockAgentCorePolicy
```

---

## Streamlit UI Issues

### Error: "No agents discovered"

**Symptom:**
Streamlit UI shows: "No agents available. Deploy agents first."

**Solution:**
```bash
# 1. Verify agent is deployed
cd finance-personal-assistant/production
uv run agentcore status

# 2. Check SSM parameter exists
AWS_PROFILE=binbash aws ssm get-parameter \
  --name "/agentcore/finance-personal-assistant/config" \
  --region us-west-2

# 3. If missing, redeploy agent
./launch.sh

# 4. Restart Streamlit
cd ../../ui
./demo.sh
```

---

### Error: "Streamlit connection error"

**Symptom:**
```
ConnectionError: Cannot connect to agent runtime
```

**Solution:**
```bash
# 1. Check agent health
cd finance-personal-assistant/production
./health.sh

# 2. Verify AWS credentials in Streamlit session
# Add to ui/app.py temporarily:
import boto3
print(boto3.Session().get_credentials())

# 3. Check SSM parameter permissions
AWS_PROFILE=binbash aws ssm get-parameters-by-path \
  --path "/agentcore" \
  --region us-west-2
```

---

### Error: "LaTeX rendering issues"

**Symptom:**
Dollar signs ($) display incorrectly in Streamlit.

**Solution:**
This is handled automatically in the code via `escape_latex()` function.

If still seeing issues:
```python
# In ui/app.py, verify escape_latex is applied:
response_text = escape_latex(response_text)
```

---

## Memory & Session Issues

### Error: "Session expired or not found"

**Symptom:**
```
SessionExpiredError: Session ID not found or expired
```

**Solution:**
- AgentCore sessions expire after inactivity
- Generate new session ID:
```python
import uuid
session_id = str(uuid.uuid4())
```

---

### Error: "Memory context too large"

**Symptom:**
```
MemoryContextError: Retrieved context exceeds token limit
```

**Solution:**
Adjust memory retrieval config in `memory_config.py`:
```python
retrieval_config = {
    "USER_PREFERENCE": {
        "top_k": 3,  # Reduce from 5
        "min_relevance": 0.8  # Increase from 0.7
    },
    # ...
}
```

---

### Error: "Cannot store memory"

**Symptom:**
```
MemoryStorageError: Failed to store memory entry
```

**Solution:**
```bash
# 1. Verify memory exists
AWS_PROFILE=binbash aws bedrock-agentcore describe-memory \
  --memory-id MEMORY-ID \
  --region us-west-2

# 2. Check IAM execution role has memory:Store permission
AWS_PROFILE=binbash aws iam get-role-policy \
  --role-name EXECUTION-ROLE \
  --policy-name BedrockAgentCorePolicy | grep "memory:Store"

# 3. Verify namespace format matches config
# Should be: finance-assistant/user/{actorId}/preferences
```

---

## OAuth/Cognito Issues

### Error: "Invalid token"

**Symptom:**
```
UnauthorizedError: Invalid JWT token
```

**Solution:**
```bash
# 1. Check Cognito User Pool configuration
AWS_PROFILE=binbash aws cognito-idp describe-user-pool \
  --user-pool-id POOL-ID

# 2. Verify token hasn't expired (default: 60 min)
# Tokens expire after 1 hour - request new token

# 3. Verify app client configuration
AWS_PROFILE=binbash aws cognito-idp describe-user-pool-client \
  --user-pool-id POOL-ID \
  --client-id CLIENT-ID
```

---

### Error: "User does not exist"

**Symptom:**
```
UserNotFoundException: User does not exist
```

**Solution:**
```bash
# Create demo user
cd finance-personal-assistant/production/cdk
python scripts/create_demo_users.py

# Or manually via AWS CLI
AWS_PROFILE=binbash aws cognito-idp admin-create-user \
  --user-pool-id POOL-ID \
  --username demo_user \
  --temporary-password "TempPass123!" \
  --user-attributes Name=email,Value=demo@example.com
```

---

### Error: "OAuth configuration not found"

**Symptom:**
Agent deployed without OAuth, but trying to access with credentials.

**Solution:**
```bash
# 1. Check if OAuth is configured
AWS_PROFILE=binbash aws ssm get-parameter \
  --name "/agentcore/finance-personal-assistant/config" | grep oauth

# 2. If missing, deploy Cognito infrastructure
cd finance-personal-assistant/production/cdk
./deploy.sh

# 3. Reconfigure and redeploy agent
cd ..
./configure.sh  # Will read OAuth from SSM
./launch.sh     # Redeploy with OAuth
```

---

## General Debugging Tips

### Enable Verbose Logging

**For Python scripts:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**For AgentCore CLI:**
```bash
export BEDROCK_AGENTCORE_LOG_LEVEL=DEBUG
uv run agentcore launch
```

---

### Check CloudWatch Logs

```bash
# List log groups
AWS_PROFILE=binbash aws logs describe-log-groups \
  --region us-west-2 | grep bedrock-agentcore

# Tail agent logs
AWS_PROFILE=binbash aws logs tail /aws/bedrock-agentcore/runtimes/AGENT-ID-DEFAULT \
  --follow \
  --format short
```

---

### Collect Diagnostic Information

```bash
# System info
echo "=== System Info ==="
uname -a
python3 --version
docker --version
aws --version
uv --version

# AWS info
echo -e "\n=== AWS Info ==="
AWS_PROFILE=binbash aws sts get-caller-identity
AWS_PROFILE=binbash aws configure get region

# Agent status
echo -e "\n=== Agent Status ==="
cd finance-personal-assistant/production
uv run agentcore status

# Recent logs
echo -e "\n=== Recent Logs ==="
AWS_PROFILE=binbash aws logs tail /aws/bedrock-agentcore/runtimes/AGENT-ID-DEFAULT \
  --since 5m \
  --format short
```

---

## Still Stuck?

1. **Review workshop notebooks**: Notebooks include inline troubleshooting tips
2. **Check CLAUDE.md**: Comprehensive architecture documentation
3. **AWS Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/
4. **AgentCore Toolkit**: https://aws.github.io/bedrock-agentcore-starter-toolkit/

---

## Workshop-Specific Quick Fixes

### "I ran commands in the wrong directory"

```bash
# Always check where you are
pwd

# Lab 1-2: Work from workshop directory
cd finance-personal-assistant/workshop

# Lab 3 & Demo: Work from production
cd finance-personal-assistant/production
```

---

### "I accidentally committed workshop artifacts"

```bash
# Reset git state
git reset HEAD

# Remove workshop-generated files
rm finance-personal-assistant/production/budget_agent.py  # If from notebook
rm finance-personal-assistant/production/main.py  # If from notebook

# Use .gitignore patterns
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
```

---

### "Workshop ran over time, need to skip ahead"

**Jump to Lab 3 (deployment):**
```bash
cd finance-personal-assistant/production
./configure.sh
./launch.sh
./health.sh
```

**Jump to Streamlit demo:**
```bash
cd ui
./demo.sh
# Open: http://localhost:8501
```

---

**Last Updated:** 2025-01-06
