# AWS AgentCore FinTech Demo - Streamlit Interface

Interactive demo for AWS AgentCore's multi-agent orchestration with real-time streaming.

## Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **AWS credentials** configured with appropriate permissions

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

## Installation

```bash
# Install dependencies
uv sync
```

## Quick Start

```bash
# Run the demo
./demo.sh

# Local mode (connects to local Docker endpoints)
./demo.sh --local
```

## Agent Discovery

Streamlit expects to read agent configurations from **SSM Parameter Store** at `/agentcore/{agent-name}/config`.

**For agents in this repo:** The `launch.sh` script calls `post_agent_deploy.py` after deployment to publish the ARN to SSM automatically.

**If SSM is not configured:** Edit `config/agents.yaml` manually:

```yaml
agents:
  your_agent_name:
    name: Your Agent Display Name
    arn: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/your_agent
    # Optional OAuth config (omit for IAM auth)
    oauth_config:
      discovery_url: https://cognito-idp.us-west-2.amazonaws.com/...
      client_id: your_client_id
```

## Usage

1. Start app: `./demo.sh`
2. Browser opens at `http://localhost:8501`
3. Select agent from sidebar
4. Login (OAuth agents) or start chatting (IAM agents)
5. Watch tool messages and streaming response

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check AWS credentials: `aws sts get-caller-identity` |
| Agent not found | Ensure agent is deployed, then restart Streamlit |
| Auth failed | Verify Cognito user exists and password is correct |
| Slow response | Normal - agents take 10-30 seconds |

## License

Based on [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) by AWS Labs.

Apache License 2.0 - See [LICENSE](../LICENSE) for details.
