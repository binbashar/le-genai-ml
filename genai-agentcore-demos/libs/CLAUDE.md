# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shared libraries for AgentCore demos. This directory provides reusable infrastructure and runtime utilities for AWS Bedrock AgentCore agents. These libraries are used across multiple agents in the `genai-agentcore-demos` project.

**Location in monorepo:** `genai-agentcore-demos/libs/`

## Directory Structure

```
libs/
├── cdk/                    # AWS CDK constructs (Python)
│   ├── agent_execution_role.py    # IAM execution role with comprehensive permissions
│   ├── agent_cognito.py           # Cognito User Pool for authentication
│   └── agent_app_client.py        # Cognito App Client configuration
│
└── python/                 # Runtime utilities
    ├── agentcore_health.py        # Health check framework (~1000 lines)
    ├── auth_utils.py              # OAuth2/JWT authentication
    ├── post_agent_deploy.py       # SSM publishing after deployment
    └── ssm_utils.py               # SSM Parameter Store utilities
```

## Architecture

### Module Organization

This is a **shared library package** used by:
- Finance Personal Assistant agent (`../finance-personal-assistant/`)
- Streamlit UI (`../ui/`)
- Future agents in the demos project

**Import pattern:**
```python
# From agent directories (use parent path insertion)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
from libs.cdk.agent_execution_role import AgentExecutionRole
```

### Design Principles

1. **Zero external dependencies for CDK constructs** - Only AWS CDK and boto3
2. **Graceful degradation** - Auth utilities work with or without OAuth configuration
3. **Reusability** - All components designed for multi-agent use
4. **Convention over configuration** - Sensible defaults with override options

## CDK Constructs (`libs/cdk/`)

### AgentExecutionRole

Creates IAM execution role with comprehensive permissions for AgentCore agents.

**File:** `agent_execution_role.py:1`

**Key features:**
- Bedrock model invocation (all models via `bedrock:InvokeModel*`)
- AgentCore Memory operations (read, write, query)
- ECR image access for agent containers
- CloudWatch logging with custom log groups
- X-Ray tracing for observability
- SSM Parameter Store access (for OAuth config)
- Optional Gateway permissions (when `enable_gateway_permissions=True`)

**Usage:**
```python
from libs.cdk.agent_execution_role import AgentExecutionRole

execution_role = AgentExecutionRole(
    scope=self,
    construct_id="ExecutionRole",
    agent_name="my-agent",
    enable_gateway_permissions=False,  # Optional
)

# Access role ARN
role_arn = execution_role.role.role_arn
```

**SSM Publishing:**
- Automatically publishes role ARN to `/agentcore/{agent_name}/execution-role-arn`
- Enables role reuse across deployments

**IAM Permissions granted:**
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- `bedrock-agentcore-memory:*` (all Memory operations)
- `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
- `xray:PutTraceSegments`, `xray:PutTelemetryRecords`
- `ssm:GetParameter` (scoped to `/agentcore/*`)

### AgentCognito

Creates Cognito User Pool with standard security configuration.

**File:** `agent_cognito.py:1`

**Key features:**
- Email-based sign-in (username is email)
- Password policy: min 8 chars, requires uppercase, lowercase, numbers, symbols
- MFA: Optional (SMS and TOTP supported)
- Account recovery via email
- Email verification required
- User self-registration enabled
- User Pool Domain for hosted UI (optional)

**Usage:**
```python
from libs.cdk.agent_cognito import AgentCognitoPool

cognito = AgentCognitoPool(
    scope=self,
    construct_id="Cognito",
    agent_name="my-agent",
)

# Access User Pool
user_pool = cognito.user_pool
user_pool_id = cognito.user_pool.user_pool_id
```

**OAuth Configuration:**
- Writes OAuth config to SSM at `/agentcore/{agent_name}/config`
- Config includes `discoveryUrl` and `allowedClients`
- Used by `configure.sh` to enable OAuth in agent deployment

### AgentAppClient

Creates Cognito App Client for user authentication.

**File:** `agent_app_client.py:1`

**Key features:**
- `USER_PASSWORD_AUTH` flow enabled
- `ALLOW_REFRESH_TOKEN_AUTH` enabled
- Token validity: Access (60 min), ID (60 min), Refresh (30 days)
- No client secret (public client for frontend apps)

**Usage:**
```python
from libs.cdk.agent_app_client import AgentAppClient

app_client = AgentAppClient(
    scope=self,
    construct_id="AppClient",
    agent_name="my-agent",
    user_pool=cognito.user_pool,
)

# Access client ID
client_id = app_client.user_pool_client.user_pool_client_id
```

## Python Utilities (`libs/python/`)

### agentcore_health.py

Comprehensive health check framework with cascading fallback.

**File:** `agentcore_health.py:1`

**Architecture:**
- **AWS Mode**: Tests deployed agent via Bedrock AgentCore Runtime
- **Local Mode**: Tests local HTTP endpoint (port 8080)
- **Cascading fallback**: Tries AWS → Local until one succeeds
- **Exit codes**: 0 for success, 1 for failure

**Key components:**

1. **AgentHealthConfig** - Configuration dataclass
   ```python
   @dataclass
   class AgentHealthConfig:
       agent_name: str              # Must match .bedrock_agentcore.yaml
       agent_dir: str               # Path to agent directory
       default_prompt: str          # Test prompt
       aws_profile: str             # AWS profile name
   ```

2. **create_health_check_cli()** - Main entry point
   - Parses CLI arguments (`--aws`, `--local`, `--timeout`)
   - Orchestrates cascading fallback
   - Returns appropriate exit codes

3. **run_health_check_aws()** - AWS mode implementation
   - Reads agent ARN from `.bedrock_agentcore.yaml`
   - Invokes via `bedrock-agentcore-runtime:InvokeAgent`
   - Handles SSE streaming response
   - Supports OAuth authentication (when configured)

4. **run_health_check_local()** - Local mode implementation
   - HTTP POST to `http://localhost:8080/invocations`
   - JSON payload format
   - Timeout handling

**Creating health checks for new agents:**

1. Create `health.py` in agent directory:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent))

   from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
   from config import get_client

   if __name__ == "__main__":
       config = AgentHealthConfig(
           agent_name="my_agent",
           agent_dir=str(Path(__file__).parent),
           default_prompt="Hello, are you operational?",
           aws_profile="binbash",
       )
       create_health_check_cli(config, get_client_func=get_client)
   ```

2. Create `health.sh`:
   ```bash
   #!/bin/bash
   uv run health.py "$@"
   ```

**Features:**
- Dynamic region detection (`AWS_REGION` → `AWS_DEFAULT_REGION` → boto3 default → `us-west-2`)
- Configurable timeout (default: 60s)
- Automatic retry with exponential backoff
- OAuth/JWT authentication support (via `auth_utils.py`)

### auth_utils.py

OAuth2/JWT authentication utilities for AgentCore agents.

**File:** `auth_utils.py:1`

**Key functions:**

1. **extract_oauth_config_from_yaml()** - Read OAuth config from `.bedrock_agentcore.yaml`
2. **authenticate()** - Get JWT token from Cognito using username/password
3. **invoke_with_token()** - Invoke agent with Bearer token authentication

**Usage:**
```python
from libs.python.auth_utils import authenticate, invoke_with_token

# Get token
token = authenticate(
    discovery_url="https://cognito-idp.us-west-2.amazonaws.com/...",
    client_id="abc123",
    username="demo@example.com",
    password="Password123!",
)

# Invoke agent with token
response = invoke_with_token(
    runtime_client=bedrock_client,
    agent_arn="arn:aws:bedrock-agentcore:...",
    token=token,
    session_id="session-123",
    prompt="Hello",
)
```

**Error handling:**
- Graceful fallback if OAuth not configured
- Clear error messages for authentication failures
- Token expiration handling

### post_agent_deploy.py

Post-deployment script to publish agent ARN to SSM.

**File:** `post_agent_deploy.py:1`

**Automatic integration:**
- Called by `launch.sh` after `agentcore launch` completes
- Reads agent ARN from `.bedrock_agentcore.yaml`
- Merges ARN into existing SSM config (preserves OAuth section)
- Writes to `/agentcore/{agent_name}/config`

**Unified SSM config structure:**
```json
{
  "arn": "arn:aws:bedrock-agentcore:...",
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://...",
      "allowedClients": ["client-id"]
    }
  }
}
```

**Usage:**
```bash
# Called automatically by launch.sh
python post_agent_deploy.py my_agent /path/to/agent/dir
```

### ssm_utils.py

SSM Parameter Store utilities for service discovery.

**File:** `ssm_utils.py:1`

**Key functions:**

1. **get_agent_config()** - Read single agent config from SSM
   ```python
   from libs.python.ssm_utils import get_agent_config

   config = get_agent_config("finance-personal-assistant", region="us-west-2")
   agent_arn = config.get("arn")
   oauth_config = config.get("oauth")
   ```

2. **get_all_agent_configs()** - Discover all deployed agents
   ```python
   from libs.python.ssm_utils import get_all_agent_configs

   agents = get_all_agent_configs(region="us-west-2")
   # Returns: {"finance-personal-assistant": {...}}
   ```

3. **put_agent_config()** - Write agent config to SSM
   ```python
   from libs.python.ssm_utils import put_agent_config

   put_agent_config(
       "my-agent",
       {"arn": "arn:aws:...", "oauth": {...}},
       region="us-west-2"
   )
   ```

**Used by:**
- Streamlit UI (`../ui/app.py`) for agent discovery
- `configure.sh` scripts to read OAuth configuration
- `post_agent_deploy.py` to publish agent ARNs

## Common Development Tasks

### Adding a New CDK Construct

1. Create file in `libs/cdk/`:
   ```python
   from aws_cdk import Stack
   from constructs import Construct

   class MyConstruct(Construct):
       def __init__(self, scope: Construct, construct_id: str, **kwargs):
           super().__init__(scope, construct_id)
           # Implementation
   ```

2. Update `libs/cdk/__init__.py`:
   ```python
   from libs.cdk.my_construct import MyConstruct

   __all__ = ["MyConstruct", ...]
   ```

3. Use in agent CDK stacks:
   ```python
   from libs.cdk.my_construct import MyConstruct

   my_construct = MyConstruct(self, "MyConstruct")
   ```

### Adding a New Python Utility

1. Create file in `libs/python/`:
   ```python
   """Utility for X functionality"""

   def my_utility_function():
       pass
   ```

2. Update `libs/python/__init__.py`:
   ```python
   from .my_utility import my_utility_function

   __all__ = ["my_utility_function", ...]
   ```

3. Use in agents:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent))

   from libs.python.my_utility import my_utility_function
   ```

### Testing Utilities Locally

```bash
# From libs directory
cd /path/to/genai-agentcore-demos/libs

# Test health check module
cd ../finance-personal-assistant/production
uv run python -c "from libs.python.agentcore_health import AgentHealthConfig; print('Import successful')"

# Test CDK constructs
cd ../finance-personal-assistant/production/cdk
uv run cdk synth
```

## Important Conventions

### Import Paths

**From agent directories:**
```python
import sys
from pathlib import Path

# Add parent directory to path (genai-agentcore-demos/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.python.agentcore_health import create_health_check_cli
from libs.cdk.agent_execution_role import AgentExecutionRole
```

**From Streamlit UI:**
```python
import sys
from pathlib import Path

# Add parent directory to path (genai-agentcore-demos/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.python.ssm_utils import get_all_agent_configs
```

### SSM Parameter Naming

All agent configurations use unified naming:
- `/agentcore/{agent_name}/config` - Unified config (ARN + OAuth)
- `/agentcore/{agent_name}/execution-role-arn` - IAM role ARN (optional)

**Best practice:** Use `ssm_utils.py` functions rather than raw boto3 calls.

### Error Handling

All utilities follow graceful degradation principles:
- OAuth utilities work without OAuth config (fall back to IAM auth)
- Health checks cascade through multiple modes
- SSM utilities return empty dict if parameter not found

### Region Configuration

All utilities respect AWS region precedence:
1. `region` parameter (explicit override)
2. `AWS_REGION` environment variable
3. `AWS_DEFAULT_REGION` environment variable
4. boto3 session default (from `~/.aws/config`)
5. Hardcoded default: `us-west-2`

## Dependencies

### CDK Constructs (`libs/cdk/`)

```toml
# No additional dependencies beyond AWS CDK
aws-cdk-lib = ">=2.0.0"
constructs = ">=10.0.0"
boto3 = "*"
```

### Python Utilities (`libs/python/`)

```toml
# Core dependencies
boto3 = "*"
pyyaml = "*"
python-dotenv = "*"
aiohttp = "*"  # For async HTTP in health checks

# Optional (for OAuth support)
requests = "*"
jwcrypto = "*"
```

## Relationship to Parent Project

This `libs/` directory is part of the `genai-agentcore-demos` project:

- **Parent CLAUDE.md**: `/Users/alex/Developer/le-genai-ml/genai-agentcore-demos/CLAUDE.md`
- **Root CLAUDE.md**: `/Users/alex/Developer/le-genai-ml/CLAUDE.md`

**Key differences:**
- Parent CLAUDE.md covers full demo architecture (agents, UI, deployment)
- This CLAUDE.md focuses on reusable library internals
- Root CLAUDE.md covers entire monorepo with all projects

## Resources

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
