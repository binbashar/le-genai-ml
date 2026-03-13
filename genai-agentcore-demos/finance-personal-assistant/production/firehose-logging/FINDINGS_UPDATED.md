# AgentCore Logging Architecture - Complete Analysis

## Executive Summary

You were **absolutely correct**! The CloudWatch GenAI dashboard IS showing model invocation data without Bedrock Model Invocation Logging enabled. The data comes from **`aws/spans` log group** (CloudWatch Transaction Search + OpenTelemetry), which is automatically created by AgentCore.

## Three Separate Logging Systems

### 1. AgentCore Runtime Logs (`/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`)

**Purpose**: Application logs from your agent code

**Contains**:
- Application-level INFO/WARN/ERROR logs
- Session management, actor IDs
- Guardrail checks
- Your custom logger.info() statements
- Python exceptions and stack traces

**Does NOT contain**:
- Model prompts/responses
- Model invocation metadata
- GenAI semantic conventions

**Format**: OpenTelemetry JSON logs

---

### 2. AWS Spans Log Group (`aws/spans`) ⭐ **WHERE GENAI DASHBOARD GETS DATA**

**Purpose**: OpenTelemetry distributed tracing spans

**Status**: ✅ **ENABLED** - 15MB of data found

**Contains**:
- **GenAI semantic conventions** (this is what the dashboard uses!)
- Model IDs: `gen_ai.request.model`
- Token counts: `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- Temperature: `gen_ai.request.temperature`
- Finish reasons: `gen_ai.response.finish_reasons`
- Request IDs, AWS regions, IAM roles
- Latency metrics (startTimeUnixNano, endTimeUnixNano)
- Error spans with exception details
- Memory operations, guardrail checks, SSM calls

**Does NOT contain**:
- **Actual prompts/responses text** (only metadata)

**Format**: OpenTelemetry span JSON with semantic conventions

**Example Span**:
```json
{
  "resource": {...},
  "scope": {
    "name": "opentelemetry.instrumentation.botocore.bedrock-runtime",
    "version": "0.54b1"
  },
  "traceId": "6920a5686c02f6ae3f019299278c5526",
  "spanId": "bd0c70fbbec67873",
  "parentSpanId": "cec7508c6d90c515",
  "name": "chat us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "kind": "CLIENT",
  "attributes": {
    "gen_ai.request.model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "gen_ai.request.temperature": 0.7,
    "gen_ai.usage.input_tokens": 2093,
    "gen_ai.usage.output_tokens": 90,
    "gen_ai.response.finish_reasons": ["end_turn"],
    "gen_ai.operation.name": "chat",
    "aws.remote.operation": "ConverseStream",
    "aws.request_id": "da8b2327-08d1-4ed3-938d-6445a2199dea",
    "session.id": "health-a69b80eb-bf18-4bb2-bd33-ab716597ae80"
  }
}
```

**How it works**:
- AgentCore automatically instruments boto3 calls with OpenTelemetry
- CloudWatch Transaction Search captures spans to `aws/spans`
- GenAI dashboard queries this log group for visualizations

---

### 3. Bedrock Model Invocation Logs (`/aws/bedrock/modelinvocations`)

**Purpose**: Complete model request/response logging

**Status**: ❌ **NOT ENABLED** (must be enabled at account level)

**Contains** (when enabled):
- **Full prompts and responses** (actual text content!)
- Complete request payloads
- Complete response payloads
- All metadata from aws/spans plus text

**Format**: Bedrock-specific JSON schema

**Example Log**:
```json
{
  "schemaType": "ModelInvocationLog",
  "schemaVersion": "1.0",
  "timestamp": "2025-11-21T17:30:00Z",
  "modelId": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "operation": "ConverseStream",
  "requestId": "abc-123",
  "input": {
    "inputBodyJson": {
      "messages": [
        {
          "role": "user",
          "content": "What is my current budget?"  // <-- ACTUAL PROMPT
        }
      ],
      "max_tokens": 4096,
      "temperature": 0.7
    }
  },
  "output": {
    "outputBodyJson": {
      "content": [
        {
          "type": "text",
          "text": "Based on your financial profile..."  // <-- ACTUAL RESPONSE
        }
      ],
      "usage": {
        "input_tokens": 1234,
        "output_tokens": 567
      }
    }
  }
}
```

---

## What the CloudWatch GenAI Dashboard Actually Shows

The GenAI observability dashboard displays data from **`aws/spans` only**:

**Metrics available**:
- ✅ Invocation counts
- ✅ Token usage (input/output)
- ✅ Latency (P50, P90, P99)
- ✅ Error rates
- ✅ Model IDs
- ✅ Request IDs for trace correlation

**NOT available** (requires Bedrock Model Invocation Logging):
- ❌ Actual prompt text
- ❌ Actual response text
- ❌ Content analysis
- ❌ Prompt/response keyword search

---

## Solution for Firehose Logging

### Option 1: Use `aws/spans` (Current Data Source) ⭐ **RECOMMENDED**

**Pros**:
- ✅ Already enabled and working
- ✅ Captures all agent invocations automatically
- ✅ Rich metadata (tokens, latency, errors)
- ✅ OpenTelemetry standard format
- ✅ No code changes required
- ✅ Industry-standard GenAI observability

**Cons**:
- ❌ No actual prompt/response text (only metadata)

**Use case**: Perfect for analytics, cost tracking, performance monitoring, error detection

**Implementation**:
```python
# CDK: Point Firehose to aws/spans
log_group_name = "aws/spans"

# Filter for model invocations only
subscription_filter_pattern = '{ $.attributes.gen_ai.request.model = * }'
```

---

### Option 2: Enable Bedrock Model Invocation Logging

**Pros**:
- ✅ Contains **full prompts and responses**
- ✅ Searchable content
- ✅ Complete audit trail
- ✅ Supports model evaluation workflows

**Cons**:
- ❌ Requires account-level enablement
- ❌ Additional storage costs
- ❌ May contain PII/sensitive data (needs masking)
- ❌ Logs can be large (100KB+ per invocation)

**Use case**: Required for content analysis, prompt engineering, model evaluation, compliance

**Implementation**:
1. Enable via Bedrock Console:
   - Bedrock → Settings → Model invocation logging
   - Enable "Text" modality
   - Choose CloudWatch Logs destination
2. CDK: Point Firehose to `/aws/bedrock/modelinvocations`

---

### Option 3: Hybrid Approach (Best of Both)

**Combine both sources**:
- Use `aws/spans` for real-time dashboards and cost tracking
- Enable Bedrock invocation logs for content analysis and auditing
- Two separate Firehose streams or unified via Lambda

**Benefits**:
- Complete observability stack
- Metadata for dashboards, content for deep analysis
- Follows AWS best practices

---

## Recommendation

### For Your Use Case

Since you want to send logs to Firehose for Bedrock Evaluations, you likely need **actual prompts and responses**, not just metadata.

**Recommended path**:

1. **Immediate**: Point Firehose to `aws/spans` for metadata
   - No setup required, works now
   - Gives you tokens, latency, errors, model IDs

2. **Next step**: Enable Bedrock Model Invocation Logging
   - Gets you full prompts/responses
   - Essential for Bedrock Evaluations
   - Can coexist with spans logging

3. **Long-term**: Combine both in your evaluation pipeline
   - Metadata from `aws/spans` for filtering
   - Content from `/aws/bedrock/modelinvocations` for evaluation

---

## Why Manual Logging Was Wrong

The initial approach of logging messages in `main.py` was problematic because:

1. **Redundant**: Data already exists in `aws/spans` (metadata) or can be enabled via Bedrock logging (content)
2. **Incomplete**: Wouldn't capture tool agent invocations (budget_agent, financial_analysis_agent)
3. **Bad Practice**: Duplicates observability responsibilities
4. **Performance**: Adds logging overhead to hot path
5. **Maintenance**: Creates technical debt
6. **Non-standard**: Doesn't follow OpenTelemetry or GenAI conventions

---

## Next Steps

**Decision point**: What data do you need for Bedrock Evaluations?

### If you need only metadata (tokens, latency, errors):
→ Use `aws/spans` immediately (already enabled)

### If you need prompts/responses for content evaluation:
→ Enable Bedrock Model Invocation Logging first

### If unsure:
→ Start with `aws/spans`, then add Bedrock logging when needed

Let me know which path you'd like to pursue, and I can help update the CDK accordingly!

---

## References

- [CloudWatch Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Transaction-Search.html)
- [Bedrock Model Invocation Logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- [CloudWatch GenAI Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/GenAI-observability.html)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
