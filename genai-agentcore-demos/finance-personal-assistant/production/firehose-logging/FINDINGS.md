# Bedrock Model Invocation Logging - Findings & Solution

## Executive Summary

The prompts and responses from Bedrock models are **NOT** in AgentCore Runtime logs. They are captured through **Bedrock Model Invocation Logging**, which must be enabled separately at the account level.

## Current State

### What We Found

1. **AgentCore Runtime Logs** (`/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`):
   - Contains application-level logs (OpenTelemetry format)
   - Session management, actor IDs, guardrail checks
   - Tool executions, errors, and performance metrics
   - **Does NOT contain model prompts/responses**

2. **Bedrock Model Invocation Logs** (`/aws/bedrock/modelinvocations`):
   - **Currently NOT enabled** in the account
   - This is where Bedrock stores actual model inputs/outputs
   - Captures all `InvokeModel`, `InvokeModelWithResponseStream`, `Converse`, `ConverseStream` calls
   - Contains full request/response data with metadata

### Why Manual Logging Was Wrong

The initial approach of manually logging messages in `main.py` was incorrect because:

1. **Redundant**: Bedrock already captures this data automatically (when enabled)
2. **Incomplete**: Wouldn't capture tool agent invocations (budget_agent, financial_analysis_agent)
3. **Bad Practice**: Duplicates observability responsibilities
4. **Performance**: Adds unnecessary logging overhead
5. **Maintenance**: Creates technical debt

## The Professional Solution

### Step 1: Enable Bedrock Model Invocation Logging

Enable this **once per AWS account/region** through the Bedrock console:

1. Go to: https://console.aws.amazon.com/bedrock
2. Navigate to **Settings** → **Model invocation logging**
3. Select data types to log:
   - ✅ Text (for prompts/responses)
   - ✅ Embedding (if using embeddings)
   - Optional: Image, Video
4. Choose destinations:
   - **CloudWatch Logs**: For real-time querying and dashboards
   - **Amazon S3**: For long-term storage and analytics
5. Configure destinations:
   - **CloudWatch**: Create log group + IAM role (automatic via console)
   - **S3**: Create bucket with proper bucket policy

**Result**: All Bedrock model invocations across your account/region will be logged automatically.

### Step 2: Configure Firehose to Subscribe to Bedrock Invocation Logs

Instead of subscribing to AgentCore Runtime logs, subscribe to Bedrock invocation logs:

**Current approach (wrong)**:
```python
# Subscribing to AgentCore Runtime logs
log_group_name = f"/aws/bedrock-agentcore/runtimes/{agent_id}-DEFAULT"
```

**Correct approach**:
```python
# Subscribe to Bedrock Model Invocation logs
log_group_name = "/aws/bedrock/modelinvocations"
```

### Step 3: Update Lambda Transformer (if needed)

The transformer lambda may need minimal adjustments since Bedrock invocation logs have a different structure:

**Bedrock Invocation Log Format**:
```json
{
  "schemaType": "ModelInvocationLog",
  "schemaVersion": "1.0",
  "timestamp": "2025-11-21T17:30:00Z",
  "accountId": "123456789012",
  "identity": {
    "arn": "arn:aws:sts::123456789012:assumed-role/..."
  },
  "region": "us-west-2",
  "requestId": "abc-123",
  "operation": "InvokeModelWithResponseStream",
  "modelId": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
  "input": {
    "inputContentType": "application/json",
    "inputBodyJson": {
      "anthropic_version": "bedrock-2023-05-31",
      "messages": [
        {
          "role": "user",
          "content": "What is my budget?"
        }
      ],
      "max_tokens": 4096,
      "temperature": 0.7
    }
  },
  "output": {
    "outputContentType": "application/json",
    "outputBodyJson": {
      "id": "msg_abc123",
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": "Based on your financial profile..."
        }
      ],
      "model": "claude-3-5-haiku-20241022",
      "stop_reason": "end_turn",
      "usage": {
        "input_tokens": 1234,
        "output_tokens": 567
      }
    }
  }
}
```

## Benefits of This Approach

### 1. Industry Standard
- Uses AWS-native observability patterns
- Follows GenAI observability best practices
- Aligns with CloudWatch GenAI dashboards

### 2. Complete Coverage
- Captures ALL Bedrock invocations (orchestrator + tool agents)
- No code changes needed to agent logic
- Automatic capture of retries, errors, streaming

### 3. Rich Metadata
- Request IDs for tracing
- Token usage and cost attribution
- Latency metrics
- Error details

### 4. Zero Code Changes
- No modifications to `main.py` or agents
- No performance overhead
- No maintenance burden

### 5. Integrated with CloudWatch GenAI Observability
- Pre-built dashboards
- Model invocation metrics
- Token usage tracking
- Error analysis

## Implementation Plan

### Phase 1: Enable Bedrock Logging (5 minutes)
1. Console: Bedrock → Settings → Model invocation logging
2. Enable Text + Embedding modalities
3. Choose CloudWatch Logs destination
4. Let console auto-create IAM role

### Phase 2: Update CDK Stack (15 minutes)
1. Change Firehose subscription from AgentCore logs to Bedrock logs
2. Update transformer lambda to parse Bedrock log format
3. Deploy CDK changes

### Phase 3: Validate (10 minutes)
1. Send test requests to agent
2. Verify logs appear in `/aws/bedrock/modelinvocations`
3. Confirm Firehose delivers to S3
4. Check CloudWatch GenAI dashboard

## Next Steps

**Before proceeding**, confirm:
1. Do you want to enable Bedrock Model Invocation Logging at the account level?
2. Should we use CloudWatch Logs, S3, or both as destinations?
3. Any compliance/security requirements for log retention?

Once confirmed, we can:
1. Enable logging via console or CDK
2. Update Firehose CDK stack to point to correct log group
3. Remove manual logging code from `main.py` (revert changes)
4. Test end-to-end flow

## References

- [Bedrock Model Invocation Logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- [CloudWatch GenAI Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/GenAI-observability.html)
- [Model Invocations Dashboard](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/model-invocations.html)
