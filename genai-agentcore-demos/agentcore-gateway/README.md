# AgentCore MCP Gateway

Generic, reusable infrastructure for exposing agent tools via AWS Bedrock AgentCore Gateway with MCP (Model Context Protocol) support.

## Overview

This Gateway infrastructure enables agents to access tools deployed as serverless Lambda functions through the Model Context Protocol (MCP). Tools can be shared across multiple agents and scaled independently.

### Key Features

- **MCP Protocol**: JSON-RPC 2.0 based tool invocation
- **Serverless Tools**: Lambda functions with auto-scaling
- **OAuth2/JWT Auth**: Cognito M2M authentication (built-in)
- **Generic & Reusable**: Serves multiple agents
- **AWS CDK**: Production-ready infrastructure as code

## Architecture

```
┌─────────────┐
│   Agent     │  (finance-personal-assistant)
│  (Strands)  │
└──────┬──────┘
       │ HTTPS + OAuth Bearer Token
       ↓
┌─────────────────────────────────────┐
│  AgentCore Gateway                  │
│  - MCP Protocol (JSON-RPC 2.0)     │
│  - OAuth2/JWT Validation (Cognito) │
│  - Tool Discovery (tools/list)     │
│  - Tool Invocation (tools/call)    │
└──────┬──────────────────────────────┘
       │ IAM Role
       ↓
┌─────────────────────────────────────┐
│  Lambda Functions (Tools)           │
│  - calculate_budget (256MB, 10s)    │
│  - [future tools...]                │
└─────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- AWS credentials configured (AWS_PROFILE=binbash or default)
- Python 3.13+
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Bedrock AgentCore access in your AWS account

### 1. Deploy Gateway Infrastructure

```bash
cd agentcore-gateway/cdk

# Deploy all CDK stacks
./deploy.sh

# Or with specific AWS profile
./deploy.sh --profile your-profile-name
```

**What gets created:**
- Cognito User Pool with M2M client for authentication
- Lambda function (`agentcore-gateway-calculate-budget`)
- AgentCore Gateway with OAuth JWT authorizer
- Gateway target (`budget_tools`)
- SSM parameters (`/agentcore/agentcore-gateway/config`)
- Secrets Manager entry for M2M credentials
- Local deployment outputs (`gateway_outputs.json`, `m2m_config.json`)

### 2. Test Gateway

```bash
# Test M2M authentication flow
cd ..
uv run python scripts/test_m2m_auth.py

# Check Gateway configuration
uv run python scripts/check_gateway_config.py

# Test via agent (recommended)
cd ../finance-personal-assistant
./health.sh
```

### 3. Cleanup (Optional)

```bash
# Destroy all CDK stacks
cd agentcore-gateway/cdk
cdk destroy --all
```

## Project Structure

```
agentcore-gateway/
├── README.md                       # This file
├── CLAUDE.md                       # Development guidance
├── pyproject.toml                  # Dependencies
├── gateway_outputs.json            # Deployment outputs (generated)
├── m2m_config.json                 # M2M credentials (generated, keep secure)
│
├── cdk/                            # AWS CDK infrastructure
│   ├── app.py                      # CDK app entry point
│   ├── deploy.sh                   # Deployment script
│   ├── post_deploy.py              # SSM/Secrets publishing
│   ├── cdk.json                    # CDK configuration
│   └── stacks/                     # CDK stack definitions
│       ├── cognito_stack.py        # Cognito User Pool + M2M client
│       ├── lambda_stack.py         # Lambda functions
│       └── gateway_stack.py        # Gateway + targets
│
├── tools/                          # MCP-compatible Lambda tools
│   ├── calculate_budget/           # Tool 1: Budget calculator
│   │   ├── main.py                 # Lambda handler (MCP format)
│   │   └── tool_schema.json        # JSON Schema for tool
│   └── [future tools...]
│
├── scripts/                        # Testing and utilities
│   ├── test_m2m_auth.py            # End-to-end Gateway testing
│   └── check_gateway_config.py     # Configuration checker
│
└── gateway-specs/                  # Specification documents
    ├── 01-mcp-protocol-essentials.md
    ├── 02-tools-inventory.md
    └── ... (comprehensive specs)
```

## Tool Development

### Adding a New Tool

1. **Create tool directory:**
   ```bash
   mkdir -p tools/my_new_tool
   ```

2. **Implement Lambda handler** (`tools/my_new_tool/main.py`):
   ```python
   import json
   import logging

   logger = logging.getLogger()
   logger.setLevel(logging.INFO)

   def handler(event, context):
       """MCP-compatible Lambda handler."""
       try:
           args = event.get('arguments', {})

           # Your tool logic here
           result = execute_tool(**args)

           # Return MCP format
           return {
               'content': [
                   {'type': 'text', 'text': str(result)}
               ]
           }
       except ValueError as e:
           raise ValueError(str(e))  # Gateway returns 400
       except Exception as e:
           raise RuntimeError(str(e))  # Gateway returns 500

   def execute_tool(**kwargs):
       """Tool-specific logic."""
       pass
   ```

3. **Define tool schema** (`tools/my_new_tool/tool_schema.json`):
   ```json
   {
     "name": "my_new_tool",
     "description": "What this tool does",
     "inputSchema": {
       "type": "object",
       "properties": {
         "param1": {
           "type": "string",
           "description": "Parameter description"
         }
       },
       "required": ["param1"]
     }
   }
   ```

4. **Update CDK Lambda stack** (`cdk/stacks/lambda_stack.py`) to include the new tool.

5. **Redeploy:**
   ```bash
   cd cdk
   ./deploy.sh
   ```

### Tool Response Format

Lambda functions must return MCP-compatible responses:

```python
{
    'content': [
        {
            'type': 'text',  # or 'image', 'resource'
            'text': 'Tool result as string'
        }
    ]
}
```

## Agent Integration

### Automatic Integration

The `finance-personal-assistant` agent automatically detects Gateway configuration from `gateway_outputs.json`. No manual configuration needed.

### Manual Integration (Other Agents)

1. **Add MCP client dependency:**
   ```bash
   pip install mcp
   ```

2. **Create MCP transport:**
   ```python
   from strands.tools.mcp.mcp_client import MCPClient
   from mcp.client.streamable_http import streamablehttp_client

   GATEWAY_ENDPOINT = "https://xxx.gateway.bedrock-agentcore.us-west-2.amazonaws.com"

   def create_transport(access_token: str):
       return streamablehttp_client(
           f"{GATEWAY_ENDPOINT}/mcp",
           headers={"Authorization": f"Bearer {access_token}"}
       )

   mcp_client = MCPClient(lambda: create_transport(access_token))
   ```

3. **Configure agent with MCP client:**
   ```python
   from strands import Agent

   agent = Agent(
       model=model,
       system_prompt=prompt,
       tools=[],  # Can mix embedded tools with Gateway tools
       mcp_client=mcp_client  # Gateway tools via MCP
   )
   ```

## Configuration

### Environment Variables

```bash
# AWS region (default: us-west-2)
export AWS_REGION=us-east-1

# AWS profile
export AWS_PROFILE=binbash

# Gateway endpoint (auto-loaded from gateway_outputs.json)
export AGENTCORE_GATEWAY_ENDPOINT=https://...
```

### Configuration Files

- **`config.py`**: Central configuration (Gateway name, Lambda settings, IAM roles)
- **`gateway_outputs.json`**: Auto-generated deployment outputs
- **`tool_schema.json`**: Per-tool JSON Schema definitions

## Testing

### Unit Testing

Test Lambda function locally:
```bash
cd tools/calculate_budget

# Create test event
cat > test_event.json <<EOF
{
  "arguments": {
    "monthly_income": 5000
  }
}
EOF

# Test locally (requires handler to be importable)
python -c "import main; print(main.handler($(cat test_event.json), None))"
```

### Integration Testing

Test via AWS Lambda:
```bash
aws lambda invoke \
  --function-name agentcore-gateway-calculate-budget \
  --payload '{"arguments": {"monthly_income": 5000}}' \
  response.json

cat response.json
```

### End-to-End Testing

Test via Gateway:
```bash
uv run python scripts/test_gateway.py
```

## Authentication

### OAuth2/JWT (Cognito)

**Auto-detected** from `finance-personal-assistant` deployment:
- User Pool ID
- Client ID
- Discovery URL

If Cognito is configured, Gateway validates JWT tokens on every request.

### IAM Authentication

**Fallback** if no Cognito configuration found. Requires AWS Signature Version 4 authentication.

## Monitoring

### CloudWatch Logs

View Lambda logs:
```bash
aws logs tail /aws/lambda/agentcore-gateway-calculate-budget --follow
```

View Gateway logs (if debug mode enabled):
```bash
# Gateway logs appear in agent runtime logs
aws logs tail /aws/bedrock-agentcore/gateways/{gateway-id} --follow
```

### CloudWatch Metrics

Standard Lambda metrics available:
- Invocations
- Duration
- Errors
- Throttles
- Concurrent Executions

Access via AWS Console → CloudWatch → Metrics → Lambda.

## Cost Estimates

**POC/MVP Usage** (1,000 invocations/month):
- Lambda compute: ~$0.20
- CloudWatch logs: ~$0.05
- Gateway: Included in AgentCore pricing
- **Total**: <$0.50/month

**Production Usage** depends on:
- Tool invocation frequency
- Lambda memory/duration
- Log retention policies

## Troubleshooting

### Gateway Returns 401 Unauthorized

**Cause**: Invalid or expired Cognito token

**Solution**:
1. Get fresh token: `python scripts/get_token.py`
2. Check token expiration (default: 1 hour)
3. Verify token audience matches Cognito client ID

### Lambda Function Not Found

**Cause**: Function deleted or wrong region

**Solution**:
1. Check deployment: `aws lambda get-function --function-name agentcore-gateway-calculate-budget`
2. Verify region: `echo $AWS_REGION`
3. Redeploy: `uv run python deploy.py`

### Gateway Target Not Found

**Cause**: Target creation failed or Gateway deleted

**Solution**:
1. List targets: `python -c "import boto3; agentcore = boto3.client('bedrock-agentcore-control'); print(agentcore.list_gateway_targets(gatewayIdentifier='<gateway-id>'))"`
2. Redeploy: `uv run python deploy.py`

### IAM Permission Denied

**Cause**: Missing permissions for Gateway or Lambda

**Solution**:
1. Check Gateway service role has `lambda:InvokeFunction`
2. Check Lambda execution role has CloudWatch Logs permissions
3. Review IAM policies in `infrastructure/iam.py`

## CDK Infrastructure

The AgentCore Gateway uses AWS CDK for all infrastructure management:

**CDK Stacks:**
1. **`cdk/stacks/cognito_stack.py`** - Cognito User Pool with M2M OAuth client
2. **`cdk/stacks/lambda_stack.py`** - Lambda functions with proper IAM roles
3. **`cdk/stacks/gateway_stack.py`** - AgentCore Gateway with custom resource targets

**Deployment:**
```bash
cd cdk
./deploy.sh
```

**Cleanup:**
```bash
cd cdk
cdk destroy --all
```

## References

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18/)
- [AWS AgentCore Gateway Docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [Strands MCP Client](https://strandsagents.com/latest/tools/mcp/)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

## Contributing

This is a POC demonstrating AgentCore Gateway capabilities. To extend:

1. Add new tools in `tools/` directory
2. Update `deploy.py` for multi-tool deployment
3. Add error handling and retry logic
4. Implement tool versioning
5. Add monitoring dashboards
6. Migrate to CDK for production deployments

## License

Apache License 2.0 - See parent repository LICENSE file.
