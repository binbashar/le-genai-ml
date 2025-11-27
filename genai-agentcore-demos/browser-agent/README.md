# Browser Agent

Minimal browser automation agent using AWS Bedrock AgentCore and Strands with AgentCoreBrowser tool for web control using natural language.

## Overview

This agent demonstrates browser automation capabilities powered by:
- **Strands Agents Framework**: Agent orchestration
- **AgentCoreBrowser**: AWS-managed browser automation (Chromium)
- **Claude Sonnet 4.5**: Reliable reasoning for complex browser tasks
- **AgentCore Runtime**: Scalable deployment with session management

## Features

- Navigate to websites using natural language
- Extract information from web pages
- Click buttons and links
- Fill out forms
- Search for content
- Take screenshots
- No local browser required (AWS-managed)

## Quick Start

### Prerequisites

- Python 3.13+
- UV package manager (`pip install uv`)
- AWS credentials configured (`AWS_PROFILE=binbash`)
- AWS Bedrock model access enabled
- Docker (for deployment)

### Local Testing

Test the agent locally without deployment:

```bash
# Install dependencies
uv sync

# Run agent interactively
uv run python browser_agent.py
```

### Deploy to AWS

Deploy to AgentCore Runtime for production use:

```bash
# 1. Configure (creates .bedrock_agentcore.yaml)
./configure.sh

# 2. Deploy to AWS
./launch.sh

# 3. Verify deployment
./health.sh
```

## Usage Examples

### Local Mode

```python
from browser_agent import browser_agent

# Simple navigation
response = browser_agent("Navigate to https://example.com and tell me what you see")

# Information extraction
response = browser_agent("Go to https://docs.aws.amazon.com and find information about AgentCore")

# Search and summarize
response = browser_agent("Search for 'AWS Bedrock' on Google and summarize the first 3 results")
```

### Deployed Mode

Invoke via AWS SDK:

```python
import boto3

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

response = client.invoke_agent_runtime(
    agentRuntimeId='browser_agent-...',
    payload={
        'prompt': 'Navigate to https://example.com'
    }
)
```

Or via HTTP:

```bash
curl -X POST https://{runtime-id}.execute-api.us-west-2.amazonaws.com/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Navigate to https://example.com"}'
```

## Sample Queries

**Basic navigation:**
- "Navigate to https://example.com and tell me what you see"
- "Go to https://github.com and describe the homepage"

**Information extraction:**
- "Visit https://docs.aws.amazon.com and find the AgentCore documentation link"
- "Go to https://news.ycombinator.com and list the top 5 article titles"

**Search and research:**
- "Search for 'Amazon Bedrock AgentCore' on Google and summarize the results"
- "Find information about Claude 4.5 on the Anthropic website"

**Interaction:**
- "Go to https://example.com/form and fill in the name field with 'Test User'"
- "Navigate to https://example.com and click the 'Learn More' button"

## Architecture

```
browser-agent/
├── main.py              # AgentCore entrypoint
├── browser_agent.py     # Browser agent with AgentCoreBrowser tool
├── config.py            # Model configuration (BedrockModelCatalog)
├── health.py            # Health check (shared module)
├── configure.sh         # Configuration wrapper
├── launch.sh            # Deployment wrapper
├── health.sh            # Health check wrapper
└── pyproject.toml       # Dependencies
```

### Key Components

**AgentCoreBrowser:**
- AWS-managed Chromium browser
- Session-based isolation (up to 8 hours)
- Live session viewing in AWS Console
- Automatic cleanup

**Model:**
- Claude Sonnet 4.5 for reliable reasoning
- Temperature: 0.7 (balanced)
- Max tokens: 4096

## Health Checks

Test deployed agent with cascading fallback:

```bash
# Cascading: AWS → Local
./health.sh

# Test AWS only
./health.sh --aws

# Test local only (requires: agentcore launch --local)
./health.sh --local

# Custom timeout
./health.sh --timeout 120
```

## Configuration

### Model Selection

Edit `browser_agent.py` to change the model:

```python
# Use Claude Haiku for faster responses
model = get_bedrock_model("strands", BedrockModelCatalog.CLAUDE_HAIKU_45)

# Use Nova Pro for cost optimization
model = get_bedrock_model("strands", BedrockModelCatalog.NOVA_PRO)
```

### Browser Region

Browser sessions are created in the same region as the agent. Configure via environment:

```bash
export AWS_REGION=us-east-1
./launch.sh
```

## Deployment Details

### What Gets Created

- **Docker container**: Browser agent code
- **ECR repository**: Container image storage
- **AgentCore Runtime**: Scalable execution environment
- **IAM execution role**: Permissions for browser, Bedrock, CloudWatch
- **CloudWatch Logs**: `/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`

### IAM Permissions Required

The AgentCore CLI automatically creates an execution role with:
- `bedrock:InvokeModel`
- `bedrock-agentcore:CreateBrowser`
- `bedrock-agentcore:StartBrowserSession`
- `bedrock-agentcore:UpdateBrowserStream`
- `bedrock-agentcore:ConnectBrowserAutomationStream`
- `ecr:GetAuthorizationToken`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### Versioning

- Version 1 created on first deployment
- New version on each `./launch.sh`
- DEFAULT endpoint points to latest version
- Previous versions remain for rollback

## Monitoring

### CloudWatch Logs

```bash
# View agent logs (extract agent-id from .bedrock_agentcore.yaml)
grep agent_arn .bedrock_agentcore.yaml
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

### Browser Session Recording

Enable session recording (optional):

```yaml
# .bedrock_agentcore.yaml
agents:
  browser_agent:
    browser_recording:
      enabled: true
      s3_bucket: my-recordings-bucket
```

## Limitations

- Session timeout: 15 minutes default, max 8 hours
- No file download capabilities by default
- Cannot handle CAPTCHAs
- Limited by browser JavaScript execution
- No persistent cookies between sessions

## Troubleshooting

### Health Check Fails

```bash
# Check deployment status
uv run agentcore status

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --since 10m

# Verify browser permissions
aws iam get-role-policy --role-name {execution-role} --policy-name BrowserPolicy
```

### Browser Session Timeout

Increase session timeout in `.bedrock_agentcore.yaml`:

```yaml
agents:
  browser_agent:
    browser_session_timeout: 3600  # 1 hour (max: 28800)
```

### Import Errors

Ensure dependencies are installed:

```bash
uv sync
```

## Cleanup

Remove all deployed resources:

```bash
# Delete Runtime, ECR, IAM role
uv run agentcore destroy
```

## Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/)
- [AWS Bedrock AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCoreBrowser API Reference](https://aws.github.io/bedrock-agentcore-starter-toolkit/)

## License

Apache License 2.0 - See LICENSE file for details.
