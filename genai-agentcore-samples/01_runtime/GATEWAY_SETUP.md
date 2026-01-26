# AgentCore Gateway Setup Guide

This guide walks you through setting up AWS Bedrock AgentCore Gateway for the translator agent with dummy tools.

## Overview

AgentCore Gateway allows you to expose Lambda functions or REST APIs as tools that agents can invoke. This setup includes:

- **Lambda Functions**: Two dummy tools (weather and text length calculation)
- **Gateway**: Routes tool calls from the agent to Lambda functions
- **Agent Integration**: Modified agent code that invokes tools through Gateway

## Architecture

```
User Request
    ↓
Agent Runtime
    ↓
LangGraph Agent
    ↓
Gateway Tool Wrapper (invokes Gateway via AWS SDK)
    ↓
AgentCore Gateway
    ↓
Lambda Functions (weather_tool, length_tool)
```

## Prerequisites

### 1. AWS CLI Configuration

Ensure you have AWS credentials configured:

```bash
aws sts get-caller-identity
```

### 2. Required AWS Permissions

Your AWS user/role needs the following permissions:

**For Lambda Deployment:**
- `lambda:CreateFunction`
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `lambda:GetFunction`
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `iam:PutRolePolicy`

**For Gateway Creation:**
- `bedrock-agentcore:CreateGateway`
- `bedrock-agentcore:GetGateway`
- `bedrock-agentcore:ListGateways`
- `bedrock-agentcore:CreateGatewayTarget`

**For Execution Role Updates:**
- `iam:GetRole`
- `iam:PutRolePolicy`
- `iam:GetRolePolicy`

**Recommended:** Use the `BedrockAgentCoreFullAccess` managed policy for initial setup, then scope down for production.

### 3. Python Dependencies

Install dependencies:

```bash
cd genai-agentcore-samples/01_runtime
uv sync
```

## Setup Steps

### Step 1: Deploy Lambda Functions

Deploy the dummy tool Lambda functions:

```bash
cd genai-agentcore-samples/01_runtime
uv run python scripts/deploy_lambda_functions.py
```

This script:
- Creates an IAM role for Lambda functions (`AgentCoreGatewayLambdaRole`)
- Deploys `weather-tool` Lambda function
- Deploys `length-tool` Lambda function
- Saves Lambda ARNs to `lambda_arns.json`

**Expected Output:**
```
============================================================
Deploying Lambda Functions for AgentCore Gateway
============================================================

1. Setting up IAM role...
✓ IAM role 'AgentCoreGatewayLambdaRole' already exists

2. Deploying Lambda functions...

   Deploying weather-tool...
✓ Created Lambda function 'weather-tool'
   ARN: arn:aws:lambda:us-west-2:ACCOUNT:function:weather-tool

   Deploying length-tool...
✓ Created Lambda function 'length-tool'
   ARN: arn:aws:lambda:us-west-2:ACCOUNT:function:length-tool

============================================================
✓ Lambda functions deployed successfully!
✓ Lambda ARNs saved to: lambda_arns.json
============================================================
```

### Step 2: Create AgentCore Gateway

Create the Gateway that will route tool calls:

```bash
uv run python scripts/create_gateway.py
```

This script:
- Creates an AgentCore Gateway named `translator-agent-gateway`
- Uses IAM for inbound authorization
- Saves Gateway ARN to `gateway_arn.json`

**Expected Output:**
```
============================================================
Creating AgentCore Gateway
============================================================

Gateway Name: translator-agent-gateway
Region: us-west-2

✓ Created Gateway 'translator-agent-gateway'
  ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:gateway/GATEWAY_ID

============================================================
✓ Gateway created successfully!
✓ Gateway ARN saved to: gateway_arn.json
============================================================
```

### Step 3: Register Lambda Targets

Register Lambda functions as Gateway targets:

```bash
uv run python scripts/register_lambda_targets.py
```

This script:
- Loads Gateway ARN and Lambda ARNs from JSON files
- Registers `get_current_weather` tool → `weather-tool` Lambda
- Registers `calculate_length` tool → `length-tool` Lambda
- Saves target ARNs to `gateway_targets.json`

**Expected Output:**
```
============================================================
Registering Lambda Targets in AgentCore Gateway
============================================================

1. Loading configuration...
   Gateway ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:gateway/GATEWAY_ID
   Lambda functions: ['weather-tool', 'length-tool']

2. Registering targets...

   Registering get_current_weather -> weather-tool...
✓ Registered target 'get_current_weather'
  Target ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:target/TARGET_ID

   Registering calculate_length -> length-tool...
✓ Registered target 'calculate_length'
  Target ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:target/TARGET_ID

============================================================
✓ All targets registered successfully!
✓ Target ARNs saved to: gateway_targets.json
============================================================
```

### Step 4: Add Gateway Permissions to Execution Role

Add necessary IAM permissions to the agent's execution role:

```bash
uv run python scripts/add_gateway_permissions.py
```

This script:
- Loads execution role ARN from `.bedrock_agentcore.yaml`
- Adds inline policy with Gateway permissions:
  - `bedrock-agentcore:InvokeGateway`
  - `bedrock-agentcore:GetGateway`
  - `ssm:GetParameter` (for Gateway config)
  - `secretsmanager:GetSecretValue` (for OAuth if needed)
  - `lambda:InvokeFunction` (for Lambda targets)

**Expected Output:**
```
============================================================
Adding Gateway Permissions to Execution Role
============================================================

1. Loading execution role ARN...
   Role ARN: arn:aws:iam::ACCOUNT:role/BedrockAgentCore-...
   Role Name: BedrockAgentCore-...

2. Adding Gateway permissions...
✓ Created policy 'AgentCoreGatewayPermissions' on role '...'

============================================================
✓ Gateway permissions added successfully!
============================================================

The execution role now has permissions to:
  - Invoke Gateway tools (bedrock-agentcore:InvokeGateway)
  - Get Gateway information (bedrock-agentcore:GetGateway)
  - Access SSM parameters for Gateway config
  - Access Secrets Manager for OAuth (if needed)
  - Invoke Lambda functions (for Gateway targets)
```

### Step 5: Configure Agent

Update `config.yaml` with the Gateway ARN:

```yaml
system_message: "You are a translator. Translate the user's message to English. Return ONLY the English translation, nothing else."
model_id: "us.amazon.nova-micro-v1:0"
temperature: 0.1
region: "us-west-2"
gateway_arn: "arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:gateway/GATEWAY_ID"
```

Alternatively, set the environment variable:

```bash
export AGENTCORE_GATEWAY_ARN="arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:gateway/GATEWAY_ID"
```

### Step 6: Deploy Agent

Deploy the updated agent to AgentCore Runtime:

```bash
uv run agentcore launch
```

## Testing

### Test Lambda Functions Directly

Test Lambda functions independently:

```bash
# Test weather tool
aws lambda invoke \
  --function-name weather-tool \
  --payload '{"location": "New York"}' \
  response.json
cat response.json

# Test length tool
aws lambda invoke \
  --function-name length-tool \
  --payload '{"text": "hello world"}' \
  response.json
cat response.json
```

### Test Gateway Tool Invocation

Test Gateway tool invocation via SDK:

```python
import boto3
import json

client = boto3.client("bedrock-agentcore", region_name="us-west-2")

# Load Gateway ARN
with open("gateway_arn.json") as f:
    gateway_data = json.load(f)
    gateway_arn = gateway_data["gatewayArn"]

# Invoke weather tool
response = client.invoke_gateway(
    gatewayArn=gateway_arn,
    toolCall={
        "name": "get_current_weather",
        "arguments": json.dumps({"location": "San Francisco"})
    }
)

print(json.dumps(response, indent=2))
```

### Test Agent with Gateway Tools

Invoke the deployed agent:

```bash
# Test translation (no tools)
uv run agentcore invoke '{"prompt": "Bonjour, comment ça va?"}'

# Test weather tool
uv run agentcore invoke '{"prompt": "What is the weather in Paris?"}'

# Test length calculation
uv run agentcore invoke '{"prompt": "How many characters are in the text hello world?"}'
```

## Troubleshooting

### Error: Gateway ARN not found

**Symptom:** `ValueError: Gateway ARN not found`

**Solution:**
1. Ensure `gateway_arn.json` exists (run `create_gateway.py`)
2. Set `gateway_arn` in `config.yaml`
3. Or set `AGENTCORE_GATEWAY_ARN` environment variable

### Error: Access Denied when invoking Gateway

**Symptom:** `AccessDeniedException` when agent tries to invoke Gateway

**Solution:**
1. Run `add_gateway_permissions.py` to add IAM permissions
2. Verify execution role has `bedrock-agentcore:InvokeGateway` permission
3. Check that Gateway ARN matches the one in IAM policy

### Error: Lambda function not found

**Symptom:** Gateway returns error about Lambda function

**Solution:**
1. Verify Lambda functions are deployed (`deploy_lambda_functions.py`)
2. Check that Lambda ARNs in `lambda_arns.json` are correct
3. Ensure Lambda functions are registered as Gateway targets (`register_lambda_targets.py`)

### Error: Tool not found in Gateway

**Symptom:** Agent reports "Unknown tool" error

**Solution:**
1. Verify tools are registered in Gateway (`register_lambda_targets.py`)
2. Check tool names match exactly: `get_current_weather` and `calculate_length`
3. Verify Gateway ARN in agent config matches the Gateway with registered tools

### Lambda Function Timeout

**Symptom:** Gateway tool calls timeout

**Solution:**
1. Check Lambda function logs in CloudWatch
2. Verify Lambda function has sufficient timeout (default: 30 seconds)
3. Check Lambda function code for errors

## Cleanup

To remove all resources:

```bash
# Delete Gateway targets (must delete targets before Gateway)
aws bedrock-agentcore delete-gateway-target \
  --gateway-arn <GATEWAY_ARN> \
  --target-arn <TARGET_ARN>

# Delete Gateway
aws bedrock-agentcore delete-gateway \
  --gateway-arn <GATEWAY_ARN>

# Delete Lambda functions
aws lambda delete-function --function-name weather-tool
aws lambda delete-function --function-name length-tool

# Delete Lambda execution role
aws iam delete-role-policy \
  --role-name AgentCoreGatewayLambdaRole \
  --policy-name <POLICY_NAME>
aws iam delete-role --role-name AgentCoreGatewayLambdaRole
```

## Next Steps

- **Add More Tools**: Create additional Lambda functions and register them as Gateway targets
- **Use REST APIs**: Instead of Lambda, register REST API endpoints as Gateway targets
- **Add Authentication**: Configure OAuth for Gateway outbound authorization
- **Monitor Usage**: Set up CloudWatch dashboards to monitor Gateway tool invocations
- **Error Handling**: Enhance error handling and retry logic in Gateway tool wrapper

## References

- [AgentCore Gateway Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

