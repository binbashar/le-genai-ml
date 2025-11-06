# Shared Python Libraries

Reusable utility modules shared across all AgentCore demo agents.

## Overview

This directory contains shared Python utilities used by multiple agents in the project. These modules promote code reuse, consistency, and maintainability across the monorepo.

**Location in project:** `genai-agentcore-demos/libs/python/`

**Import pattern:**
```python
# Add parent path to sys.path (for agent scripts)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import shared modules
from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
from libs.python.auth_utils import authenticate, invoke_with_token
from libs.python.ssm_utils import get_all_agent_configs, get_agent_config
from libs.python.post_agent_deploy import publish_agent_config
```

---

## Modules

### 1. agentcore_health.py

**Purpose:** Comprehensive health check module for AgentCore agents

**Key features:**
- Cascading fallback strategy (AWS → Local)
- Dynamic region detection (respects `AWS_REGION` env var)
- Configurable timeout via CLI flags
- Detailed error reporting with suggestions
- Support for both OAuth and IAM authentication
- Shared across all agents for consistency

**Usage:**

Create minimal health check script in agent directory:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli
from config import get_client

if __name__ == "__main__":
    config = AgentHealthConfig(
        agent_name="your_agent_name",
        agent_dir=str(Path(__file__).parent),
        default_prompt="Hello, are you operational?",
        aws_profile="binbash",
    )
    create_health_check_cli(config, get_client_func=get_client)
```

**CLI usage:**
```bash
./health.sh                 # Cascading: Try AWS, fallback to Local
./health.sh --aws           # Test only AWS deployment
./health.sh --local         # Test only local HTTP endpoint
./health.sh --timeout 120   # Custom timeout (default: 60 seconds)
```

**Configuration:**

```python
@dataclass
class AgentHealthConfig:
    agent_name: str              # Agent name (matches .bedrock_agentcore.yaml)
    agent_dir: str               # Directory containing agent code
    default_prompt: str          # Test prompt to send
    aws_profile: str             # AWS profile to use (default: "binbash")
    local_port: int              # Local HTTP port (default: 8080)
    timeout_seconds: int         # Timeout per mode (default: 60)
```

**Exit codes:**
- `0` - Agent healthy (AWS or Local)
- `1` - Agent unhealthy or unreachable

**Key functions:**

- `create_health_check_cli(config, get_client_func)` - Main CLI entry point
- `check_aws_health(config, client)` - Test deployed agent via boto3
- `check_local_health(config)` - Test local HTTP endpoint
- `get_agent_arn_from_config(config)` - Read ARN from .bedrock_agentcore.yaml

**Benefits:**
- ~1000 lines of robust health checking logic
- No duplication across agents
- Automatic cascading fallback
- Consistent error messages

---

### 2. auth_utils.py

**Purpose:** OAuth2/JWT authentication and agent invocation with tokens

**Key features:**
- Cognito ROPC (Resource Owner Password Credentials) authentication
- JWT token management
- Agent invocation with Bearer token
- HTTP streaming support via requests library
- Graceful error handling

**Usage:**

**Authentication:**
```python
from libs.python.auth_utils import authenticate

# Authenticate user with Cognito
auth_config = {
    "discovery_url": "https://cognito-idp.us-west-2.amazonaws.com/...",
    "client_id": "abc123"
}
token_dict = authenticate(auth_config, username="demo", password="DemoPass123!")
# Returns: {"access_token": "eyJ...", "id_token": "eyJ...", "expires_in": 3600}
```

**Agent invocation:**
```python
from libs.python.auth_utils import invoke_with_token

# Invoke agent with JWT token
response_stream = invoke_with_token(
    agent_arn="arn:aws:bedrock-agentcore:us-west-2:...",
    token=token_dict["access_token"],
    prompt="Hello, are you operational?",
    session_id="test-session-123",
    region="us-west-2",
    timeout=60
)

# Stream response
for line in response_stream.iter_lines():
    if line.startswith(b'data:'):
        event = json.loads(line[5:].decode('utf-8'))
        print(event)
```

**Key functions:**

- `authenticate(auth_config, username, password)` → `dict`
  - Authenticates user with Cognito ROPC flow
  - Returns token dictionary with access_token, id_token, expires_in

- `invoke_with_token(agent_arn, token, prompt, session_id, region, timeout)` → `Response`
  - Invokes agent with Bearer token authentication
  - Returns streaming HTTP response (requests.Response object)
  - Use `.iter_lines()` for SSE streaming

- `get_agent_endpoint_url(agent_arn, region)` → `str`
  - Constructs agent invocation URL from ARN
  - Format: `https://bedrock-agentcore.{region}.amazonaws.com/...`

**Used by:**
- Streamlit UI (`ui/app.py`) for OAuth-protected agents
- Health checks (`agentcore_health.py`) for OAuth agents
- Workshop notebooks for authentication examples

---

### 3. post_agent_deploy.py

**Purpose:** Publish agent ARN to SSM Parameter Store after deployment

**Workflow integration:**

```bash
# Deployment script (launch.sh)
uv run agentcore launch --auto-update-on-conflict   # 1. Deploy agent
uv run python ../libs/python/post_agent_deploy.py AGENT_NAME .   # 2. Publish ARN to SSM
```

**What it does:**
1. Reads agent ARN from `.bedrock_agentcore.yaml`
2. Reads existing SSM parameter (if exists) to preserve OAuth config
3. Updates SSM parameter with agent ARN (merged with existing config)
4. Enables Streamlit UI auto-discovery

**Usage:**

```bash
# From agent directory (with .bedrock_agentcore.yaml present)
uv run python ../libs/python/post_agent_deploy.py finance_personal_assistant .

# Arguments:
#   AGENT_NAME - Snake_case agent name (e.g., finance_personal_assistant)
#   AGENT_DIR  - Directory containing .bedrock_agentcore.yaml (usually ".")
```

**SSM parameter structure:**

**Before post-deploy (from CDK):**
```json
{
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.../.well-known/openid-configuration",
      "allowedClients": ["abc123"]
    }
  }
}
```

**After post-deploy:**
```json
{
  "arn": "arn:aws:bedrock-agentcore:us-west-2:...:runtime/finance_personal_assistant-ABC123",
  "oauth": {
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.../.well-known/openid-configuration",
      "allowedClients": ["abc123"]
    }
  }
}
```

**Key functions:**

- `publish_agent_config(agent_name, agent_dir)` → `None`
  - Main function called by launch.sh
  - Reads ARN, merges with OAuth config, publishes to SSM

- `get_agent_arn_from_yaml(yaml_path)` → `str`
  - Extracts agent ARN from .bedrock_agentcore.yaml
  - Handles nested structure: `agents.{agent_name}.bedrock_agentcore.agent_arn`

**Error handling:**
- Gracefully handles missing .bedrock_agentcore.yaml (warns but doesn't fail)
- Preserves existing SSM config (merges instead of overwriting)
- Validates ARN format before publishing

---

### 4. ssm_utils.py

**Purpose:** SSM Parameter Store utilities for service discovery

**Key features:**
- Discover all deployed agents from SSM
- Read individual agent configurations
- Type-safe configuration parsing
- Region-aware (uses boto3 session default)

**Usage:**

**Discover all agents:**
```python
from libs.python.ssm_utils import get_all_agent_configs

# Returns dict of all agent configs
agent_configs = get_all_agent_configs()
# {
#   "finance_personal_assistant": {
#     "arn": "arn:aws:bedrock-agentcore:...",
#     "oauth": {"customJWTAuthorizer": {...}}
#   },
#   "market_trends_agent": {
#     "arn": "arn:aws:bedrock-agentcore:..."
#   }
# }

# Use in Streamlit UI
for agent_key, agent_info in agent_configs.items():
    print(f"Agent: {agent_key}")
    print(f"  ARN: {agent_info['arn']}")
    if agent_info.get('oauth'):
        print("  Auth: OAuth/Cognito")
    else:
        print("  Auth: IAM")
```

**Get specific agent config:**
```python
from libs.python.ssm_utils import get_agent_config

config = get_agent_config("finance_personal_assistant")
# Returns: {"arn": "...", "oauth": {...}}
```

**Key functions:**

- `get_all_agent_configs(region=None)` → `dict[str, dict]`
  - Scans `/agentcore/*/config` parameters
  - Returns dict mapping agent names to configurations
  - Gracefully handles parsing errors (skips invalid configs)

- `get_agent_config(agent_name, region=None)` → `dict | None`
  - Reads single agent config from SSM
  - Returns None if parameter doesn't exist
  - Validates JSON structure

**SSM parameter pattern:**
- Path: `/agentcore/{agent_name}/config`
- Value: JSON string with `arn` and optional `oauth` fields
- Type: String
- Created by: CDK (OAuth part) + launch.sh (ARN part)

**Used by:**
- Streamlit UI (`ui/app.py`) for agent discovery
- Health checks for discovering agent endpoints
- Workshop scripts for dynamic configuration

**Region handling:**
```python
# Uses boto3 session default region if not specified
# Priority: region parameter > AWS_REGION env var > boto3 default
```

---

## Dependency Management

These shared modules are part of the parent package `genai-agentcore-demos`.

**Root `pyproject.toml`:**
```toml
[project]
name = "genai-agentcore-demos"
version = "0.1.0"
dependencies = [
    "boto3>=1.35.80",
    "botocore",
    "pyyaml",
    "requests",
    "aiohttp",
]
```

**Agent `pyproject.toml`:**
```toml
dependencies = [
    "genai-agentcore-demos",  # Includes shared libs
    # ... agent-specific dependencies
]
```

**Installation:**
```bash
# From project root (installs shared libs)
cd genai-agentcore-demos
uv sync

# From agent directory (includes parent package)
cd finance-personal-assistant/production
uv sync
```

---

## Path Resolution Pattern

All shared modules use absolute paths from project root:

```python
# In agent's health.py or main.py
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Now you can import shared libs
from libs.python.agentcore_health import AgentHealthConfig
```

**Directory structure context:**
```
genai-agentcore-demos/                    # Project root
├── libs/
│   └── python/
│       ├── agentcore_health.py          # This file
│       ├── auth_utils.py
│       ├── ssm_utils.py
│       └── post_agent_deploy.py
│
├── finance-personal-assistant/
│   └── production/
│       ├── health.py                    # Path(__file__).parent.parent.parent → root
│       └── main.py
│
└── ui/
    └── app.py
```

---

## Testing

**Unit tests:** (coming soon)
```bash
# From project root
pytest libs/python/tests/
```

**Manual testing:**

**Health checks:**
```bash
cd finance-personal-assistant/production
./health.sh --aws
./health.sh --local
```

**Authentication:**
```python
from libs.python.auth_utils import authenticate

auth_config = {
    "discovery_url": "https://cognito-idp.us-west-2.amazonaws.com/...",
    "client_id": "abc123"
}
token = authenticate(auth_config, "demo_user", "DemoPass123!")
print(f"Token: {token['access_token'][:20]}...")
```

**SSM discovery:**
```python
from libs.python.ssm_utils import get_all_agent_configs

configs = get_all_agent_configs()
print(f"Found {len(configs)} agents")
```

---

## Best Practices

### Using Shared Modules

**DO:**
- ✅ Import shared modules at the top of your file
- ✅ Use `Path(__file__).parent` for relative path resolution
- ✅ Handle exceptions from shared modules gracefully
- ✅ Pass configuration via dataclasses (e.g., AgentHealthConfig)

**DON'T:**
- ❌ Modify shared modules for agent-specific logic (extend instead)
- ❌ Hardcode paths or regions in shared modules
- ❌ Import from relative paths (`from ..libs.python import ...`)
- ❌ Duplicate shared logic in agent code

### Adding New Shared Modules

**Checklist:**
1. Create module in `libs/python/`
2. Add docstrings and type hints
3. Export key functions in `__init__.py`
4. Update this README with usage examples
5. Test in at least 2 agents (ensure reusability)
6. Add dependencies to root `pyproject.toml` (if needed)

---

## Migration Notes

### Moving from Duplicated Code

**Before (duplicated across agents):**
```python
# In each agent: health.py
def check_aws_health():
    # 100 lines of health checking logic
    pass
```

**After (shared module):**
```python
# In each agent: health.py
from libs.python.agentcore_health import AgentHealthConfig, create_health_check_cli

config = AgentHealthConfig(...)
create_health_check_cli(config)
```

**Benefits:**
- Single source of truth (~1000 lines → ~10 lines per agent)
- Bug fixes propagate to all agents
- Consistent behavior and error messages

---

## Troubleshooting

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'libs'`

**Solution:**
```python
# Add this at the top of your agent script
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

**Verify path:**
```python
print(Path(__file__).parent.parent.parent)  # Should print project root
```

---

### SSM Parameter Not Found

**Error:** `ParameterNotFound: /agentcore/finance_personal_assistant/config`

**Solution:**
```bash
# Verify agent deployed
cd finance-personal-assistant/production
grep agent_arn .bedrock_agentcore.yaml

# Publish ARN to SSM
uv run python ../libs/python/post_agent_deploy.py finance_personal_assistant .

# Verify parameter exists
aws ssm get-parameter --name "/agentcore/finance_personal_assistant/config"
```

---

### Authentication Failed

**Error:** `AuthenticationError: Invalid username or password`

**Check:**
1. Cognito User Pool deployed: `aws cognito-idp list-user-pools --max-results 10`
2. User exists: `aws cognito-idp admin-get-user --user-pool-id POOL_ID --username demo`
3. Password correct (check `.demo_users.json`)
4. Client ID matches: Check SSM parameter vs Cognito Console

---

## License & Attribution

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

**License:** Apache License 2.0 - See LICENSE for details.

**Last Updated:** 2025-01-06
