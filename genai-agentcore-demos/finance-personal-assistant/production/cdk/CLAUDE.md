# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This directory contains the CDK infrastructure code for deploying the Finance Personal Assistant's OAuth2/Cognito authentication and IAM execution role. It is part of the production deployment architecture for the Finance Personal Assistant agent.

**Location in project hierarchy:** `genai-agentcore-demos/finance-personal-assistant/production/cdk/`

**Purpose:** Deploys authentication infrastructure (Cognito User Pool + App Client) and IAM execution role, publishes OAuth configuration to SSM Parameter Store for automatic discovery by `configure.sh` and the Streamlit UI.

## Common Commands

### Deploy Infrastructure

```bash
# Deploy all stacks (Cognito + IAM + OAuth config to SSM)
./deploy.sh

# Deploy with explicit region/profile
AWS_PROFILE=binbash AWS_REGION=us-west-2 ./deploy.sh
```

**What happens:**
1. Checks for `.demo_users.json` in parent directory (`../../.demo_users.json`)
2. Bootstraps CDK if needed (idempotent)
3. Deploys CDK stack with `--require-approval never`
4. Outputs saved to `outputs.json`
5. Creates SSM parameters:
   - `/agentcore/finance_personal_assistant/config` - OAuth configuration (discovery URL, allowed clients)
   - `/agentcore/finance_personal_assistant/execution-role-arn` - IAM role ARN
   - `/agentcore/shared/cognito-pool-id` - Shared Cognito Pool ID

### Manual CDK Commands

```bash
# Synthesize CloudFormation template
uv run cdk synth

# View differences before deployment
uv run cdk diff

# List all stacks
uv run cdk list

# Destroy all stacks
uv run cdk destroy --all
```

### Bootstrap CDK (One-Time Setup)

```bash
# Export environment variables (required)
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region || echo "us-west-2")

# Bootstrap CDK in the account/region
uv run cdk bootstrap
```

**Note:** The `deploy.sh` script automatically exports these environment variables and runs bootstrap if needed.

## Architecture

### CDK Stack Structure

The CDK app creates a single stack (`finance-personal-assistant-stack`) with three main constructs:

1. **AgentCognitoPool** (`libs/cdk/agent_cognito.py`):
   - Creates Cognito User Pool
   - Reads demo users from `../../.demo_users.json` (if exists)
   - Creates users with pre-verified emails
   - Publishes Pool ID to SSM: `/agentcore/shared/cognito-pool-id`

2. **AgentAppClient** (`libs/cdk/agent_app_client.py`):
   - Creates Cognito App Client for user authentication
   - Enables `USER_PASSWORD_AUTH` flow
   - Configures token validity (access: 60min, ID: 60min, refresh: 30 days)
   - **Publishes OAuth config to SSM**: `/agentcore/finance_personal_assistant/config`
   - OAuth config includes discovery URL and allowed client IDs

3. **AgentExecutionRole** (`libs/cdk/agent_execution_role.py`):
   - Creates IAM role for AgentCore Runtime execution
   - Comprehensive permissions:
     - Bedrock model invocation and guardrails
     - AgentCore Memory operations (Create, Get, List, Delete, Retrieve)
     - AgentCore Runtime invocation
     - ECR image access
     - CloudWatch logging
     - X-Ray tracing
     - Token vault access (OAuth2, API keys)
     - Code Interpreter access
   - AssumeRole conditions (SourceAccount, SourceArn)
   - **Publishes role ARN to SSM**: `/agentcore/finance_personal_assistant/execution-role-arn`

### Service Discovery Pattern

**SSM Parameter Store as configuration registry:**

After CDK deployment, configuration is automatically available to downstream services:

```
/agentcore/finance_personal_assistant/config
{
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_abc123/.well-known/openid-configuration",
      "allowedClients": ["4v0e3082h9a6dssu9ts4b5crct"]
    }
  }
  // "arn" field added later by ../launch.sh after agent deployment
}
```

**Consumers:**
- `../configure.sh` - Reads OAuth config during agent configuration
- `../launch.sh` - Appends agent ARN to config after deployment
- `../../../ui/app.py` - Streamlit UI discovers all agents at runtime

### Demo Users Pattern

**File location:** `../../.demo_users.json` (two levels up from this cdk/ directory)

**Example structure:**
```json
[
  {
    "username": "demo",
    "password": "TempPass123!",
    "email": "demo@example.com",
    "name": "Demo User"
  }
]
```

**Usage:**
- Copy `../../.demo_users.json.example` to `../../.demo_users.json`
- Customize usernames, passwords, emails, names
- Run `./deploy.sh` - users are created automatically
- Passwords should be changed on first login (standard Cognito flow)

**Note:** Demo users are optional. If `.demo_users.json` doesn't exist, deployment proceeds without creating users (you can create users manually via Cognito Console).

## Shared CDK Constructs

This CDK app uses reusable constructs from `../../../libs/cdk/`:

### AgentCognitoPool

**Purpose:** Create Cognito User Pool with standard security configuration

**Key features:**
- Case-insensitive sign-in
- Password policy (min 8 chars)
- Self-sign-up disabled (admin-only user creation)
- Email verification enabled
- Account recovery via phone/email
- Optional demo user creation from JSON file
- Publishes Pool ID to SSM for reuse

**Usage in app.py:**
```python
from libs.cdk.agent_cognito import AgentCognitoPool

cognito_pool = AgentCognitoPool(
    self,
    "CognitoPool",
    pool_name="finance-personal-assistant",
    demo_users_file=Path(__file__).parent.parent / ".demo_users.json",
)
```

### AgentAppClient

**Purpose:** Create Cognito App Client and publish OAuth config to SSM

**Key features:**
- USER_PASSWORD_AUTH enabled (direct user/pass login)
- ALLOW_REFRESH_TOKEN_AUTH enabled
- Configurable token validity
- Publishes unified OAuth configuration to SSM
- Configuration includes OIDC discovery URL and allowed clients

**Usage in app.py:**
```python
from libs.cdk import AgentAppClient

app_client = AgentAppClient(
    self,
    "AppClient",
    agent_name=agent_name,
    user_pool=cognito_pool.user_pool,
)
```

**SSM parameter created:**
- Name: `/agentcore/{agent_name}/config`
- Value: JSON with OAuth configuration
- Type: String
- Overwrite: True (idempotent)

### AgentExecutionRole

**Purpose:** Create IAM execution role with comprehensive AgentCore permissions

**Key features:**
- AssumeRole by `bedrock-agentcore.amazonaws.com` service
- Source account and ARN validation
- 15+ permission statements covering:
  - Bedrock model invocation and guardrails
  - AgentCore Memory full CRUD
  - AgentCore Runtime invocation
  - ECR image access
  - CloudWatch logging and X-Ray tracing
  - Token vault access (OAuth2, API keys)
  - Code Interpreter access
  - Optional Gateway permissions (disabled for this agent)
- Publishes role ARN to SSM for reuse

**Usage in app.py:**
```python
from libs.cdk import AgentExecutionRole

execution_role = AgentExecutionRole(
    self,
    "ExecutionRole",
    agent_name=agent_name,
    enable_gateway_permissions=False,  # No Gateway in this project
)
```

**SSM parameter created:**
- Name: `/agentcore/{agent_name}/execution-role-arn`
- Value: Role ARN
- Type: String

## Integration with Agent Deployment

### Configuration Flow

1. **CDK Deployment** (`./deploy.sh`):
   - Creates Cognito User Pool + App Client
   - Creates IAM execution role
   - Publishes OAuth config to SSM: `/agentcore/finance_personal_assistant/config`
   - Publishes role ARN to SSM: `/agentcore/finance_personal_assistant/execution-role-arn`
   - Saves outputs to `outputs.json`

2. **Agent Configuration** (`../configure.sh`):
   - Reads OAuth config from SSM
   - Creates `.bedrock_agentcore.yaml` with:
     - OAuth authorizer configuration
     - Request header allowlist
     - Entrypoint: `main.py`
     - Memory: disabled (using custom memory config)

3. **Agent Deployment** (`../launch.sh`):
   - Runs `agentcore launch` (builds Docker, deploys to AgentCore Runtime)
   - Runs `post_agent_deploy.py` (publishes agent ARN to SSM)
   - SSM config updated: `/agentcore/finance_personal_assistant/config` now includes agent ARN

4. **Streamlit Discovery** (`../../../ui/app.py`):
   - Reads all configs from `/agentcore/*/config`
   - Auto-discovers finance-personal-assistant agent
   - Uses OAuth config for authentication

### SSM Parameter Lifecycle

**Created by CDK:**
```json
// /agentcore/finance_personal_assistant/config
{
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/.../",
      "allowedClients": ["..."]
    }
  }
}
```

**Updated by ../launch.sh:**
```json
// /agentcore/finance_personal_assistant/config
{
  "arn": "arn:aws:bedrock-agentcore:us-west-2:...:runtime/...",
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/.../",
      "allowedClients": ["..."]
    }
  }
}
```

**Removal:**
```bash
# Delete config parameter (reverts to IAM auth)
aws ssm delete-parameter --name "/agentcore/finance_personal_assistant/config"

# Reconfigure agent without OAuth
cd .. && ./configure.sh  # Falls back to IAM authentication
```

## Deployment Artifacts

### outputs.json

**Generated by:** CDK deployment (`cdk deploy --outputs-file outputs.json`)

**Example structure:**
```json
{
  "finance-personal-assistant-stack": {
    "UserPoolId": "us-west-2_abc123",
    "ClientId": "4v0e3082h9a6dssu9ts4b5crct",
    "ExecutionRoleArn": "arn:aws:iam::123456789012:role/...",
    "ExecutionRoleName": "BedrockAgentCore-finance_personal_assistant-execution-role"
  }
}
```

**Usage:** Referenced by post-deployment scripts (currently informational only)

**Git status:** Not committed (deployment-specific)

### cdk.out/

**Purpose:** CDK synthesis output (CloudFormation templates, asset manifests)

**Git status:** Not committed

**Key files:**
- `finance-personal-assistant-stack.template.json` - CloudFormation template
- `tree.json` - Construct tree visualization
- `manifest.json` - Asset manifest

## Important Conventions

### Agent Naming

**Variable:** `agent_name = "finance_personal_assistant"`
- Used in SSM parameter paths
- Used in IAM role names
- Used in OAuth config keys
- **Format:** snake_case (underscores, not hyphens)

**Stack prefix:** `stack_prefix = "finance-personal-assistant"`
- Used in CloudFormation stack name
- **Format:** kebab-case (hyphens, not underscores)

### Environment Variables

CDK requires environment configuration for account/region resolution:

```python
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)
```

**Set by deploy.sh:**
```bash
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region || echo "us-west-2")
```

### Path Resolution

**Shared constructs import:**
```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from libs.cdk import AgentAppClient, AgentExecutionRole
```

**Demo users file:**
```python
demo_users_file=Path(__file__).parent.parent / ".demo_users.json"
```

**Pattern:** Use `Path(__file__).parent` for relative path resolution (portable across environments)

### Resource Tagging

**Standard tags applied to all resources:**
```python
Tags.of(app).add("Project", "GenAI-AgentCore-Demos")
Tags.of(app).add("Agent", "FinancePersonalAssistant")
Tags.of(app).add("ManagedBy", "CDK")
```

**Purpose:** Cost tracking, resource filtering, compliance

## AWS Configuration

### Required Permissions

**For CDK deployment:**
- CloudFormation: CreateStack, UpdateStack, DeleteStack, DescribeStacks
- IAM: CreateRole, PutRolePolicy, AttachRolePolicy, DeleteRole
- Cognito: CreateUserPool, CreateUserPoolClient, CreateUserPoolUser
- SSM: PutParameter, GetParameter, DeleteParameter
- Lambda: CreateFunction (for CDK Custom Resources)
- S3: CreateBucket, PutObject (for CDK asset storage)

**Recommended:** Use administrator access for initial CDK bootstrap and deployment.

### Default Profile

**Profile:** `AWS_PROFILE=binbash`

**Verify:**
```bash
export AWS_PROFILE=binbash
aws sts get-caller-identity
```

### Region Configuration

**Priority order:**
1. `CDK_DEFAULT_REGION` environment variable
2. `aws configure get region` output
3. Hardcoded fallback: `us-west-2`

**Set explicitly:**
```bash
export CDK_DEFAULT_REGION=us-west-2
```

## Troubleshooting

### CDK Bootstrap Failed

**Symptoms:** `cdk deploy` fails with "CDK toolkit stack does not exist"

**Solution:**
```bash
# Ensure environment variables are set
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region || echo "us-west-2")

# Bootstrap explicitly
uv run cdk bootstrap
```

### Demo Users Not Created

**Symptoms:** Deployment succeeds but no users in Cognito Console

**Diagnosis:**
```bash
# Check if demo users file exists
ls -la ../../.demo_users.json

# Verify file is valid JSON
cat ../../.demo_users.json | jq .
```

**Solution:**
```bash
# Copy example file
cp ../../.demo_users.json.example ../../.demo_users.json

# Edit with your users
# Redeploy
./deploy.sh
```

### SSM Parameter Not Found

**Symptoms:** `../configure.sh` fails with "Parameter not found"

**Diagnosis:**
```bash
# Check if parameter exists
aws ssm get-parameter --name "/agentcore/finance_personal_assistant/config"

# List all agentcore parameters
aws ssm get-parameters-by-path --path "/agentcore/" --recursive
```

**Solution:**
```bash
# Redeploy CDK (creates SSM parameters)
./deploy.sh

# Verify creation
aws ssm get-parameter --name "/agentcore/finance_personal_assistant/config"
```

### Custom Resource Lambda Timeout

**Symptoms:** Deployment hangs or fails with Lambda timeout error

**Cause:** SSM PutParameter operation taking too long (rare)

**Solution:**
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
    --stack-name finance-personal-assistant-stack \
    --max-items 20

# Retry deployment (CDK is idempotent)
./deploy.sh
```

### IAM Permission Errors

**Symptoms:** Agent fails to invoke models or access memory

**Diagnosis:**
```bash
# Check execution role permissions
aws iam get-role-policy \
    --role-name BedrockAgentCore-finance_personal_assistant-execution-role \
    --policy-name ExecutionRoleDefaultPolicyFD14B40F
```

**Solution:** The `AgentExecutionRole` construct includes comprehensive permissions. If errors persist:
1. Check AWS service quotas (Bedrock model access)
2. Verify model access is enabled in Bedrock Console
3. Check CloudTrail for AccessDenied events

## Cleanup

### Delete All Resources

```bash
# Destroy CDK stack (deletes Cognito, IAM, SSM parameters)
uv run cdk destroy --all

# Confirm deletion
aws cloudformation list-stacks --stack-status-filter DELETE_COMPLETE
```

**Note:** Cognito User Pool has `RETAIN` removal policy by default. To force delete:
```bash
# Get User Pool ID from outputs.json
USER_POOL_ID=$(jq -r '.["finance-personal-assistant-stack"].UserPoolId' outputs.json)

# Delete User Pool manually
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
```

### Remove SSM Parameters Only

```bash
# Delete OAuth config
aws ssm delete-parameter --name "/agentcore/finance_personal_assistant/config"

# Delete execution role ARN
aws ssm delete-parameter --name "/agentcore/finance_personal_assistant/execution-role-arn"

# Delete shared Cognito pool ID
aws ssm delete-parameter --name "/agentcore/shared/cognito-pool-id"
```

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License:** Apache License 2.0 - See LICENSE for details.
