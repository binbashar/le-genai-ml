# Schemas - Canonical Reference

**Single source of truth for all data schemas in the evaluation pipeline.**

## Data Flow

```
Bedrock Log (JSON) → Staging Parquet (17 cols) → Evaluation JSONL (2 fields)
```

---

## Date Format Specification

### Input Dates (Step Function Parameters)

- **Accepted formats**:
  - Full ISO 8601 UTC: `YYYY-MM-DDTHH:MM:SSZ` (e.g., `"2025-11-25T00:00:00Z"`) - **recommended**
  - Date only: `YYYY-MM-DD` (e.g., `"2025-11-25"`) - backward compatible
- **Timezone**: All dates are interpreted as **UTC**
- **Default times** (for date-only format):
  - `start_date`: `00:00:00 UTC` (beginning of day)
  - `end_date`: `23:59:59 UTC` (end of day)
- **Range**: Both `start_date` and `end_date` are **inclusive**

### Examples

```json
// Full ISO 8601 UTC (recommended)
{
  "start_date": "2025-11-25T00:00:00Z",
  "end_date": "2025-11-25T23:59:59Z"
}

// Date-only (backward compatible, normalized internally)
{
  "start_date": "2025-11-25",
  "end_date": "2025-11-25"
}
// Normalized to: start=2025-11-25T00:00:00Z, end=2025-11-25T23:59:59Z
```

---

## 1. Bedrock Invocation Log

**Source**: CloudWatch Logs (`bedrock-model-invocations`)
**Format**: JSON (Converse API)
**Validated**: 2025-11-25

```json
{
  "timestamp": "2025-11-25T13:10:36Z",
  "modelId": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "requestId": "73ecc88e-d2a5-44ef-acae-f13cfb0e5a56",
  "operation": "ConverseStream",
  "region": "us-west-2",
  "identity": {
    "arn": "arn:aws:sts::ACCOUNT:assumed-role/BedrockAgentCore-finance_personal_assistant-execution-role/..."
  },
  "input": {
    "inputBodyJson": {
      "messages": [
        {"role": "user", "content": [{"text": "Hello, are you operational?"}]}
      ],
      "system": [{"text": "You are a financial advisor..."}],
      "inferenceConfig": {"temperature": 0.7}
    },
    "inputTokenCount": 1959
  },
  "output": {
    "outputBodyJson": {
      "output": {
        "message": {
          "content": [{"text": "¡Hola! Yes, I'm fully operational..."}]
        }
      },
      "stopReason": "end_turn",
      "metrics": {"latencyMs": 3176},
      "usage": {
        "inputTokens": 1959,
        "outputTokens": 89,
        "totalTokens": 2048
      }
    },
    "outputTokenCount": 89
  }
}
```

**Extraction Paths** (implemented in `cdk/lambda/transform_bedrock_logs/schema.py`):
- `agent_name`: `identity.arn` → regex `BedrockAgentCore-(.+?)-execution-role` (AgentCore Runtime name)
- `prompt`: `input.inputBodyJson.messages[-1].content[].text` (last user message)
- `response`: `output.outputBodyJson.output.message.content[].text`
- `system_prompt`: `input.inputBodyJson.system[].text`
- `input_tokens`: `output.outputBodyJson.usage.inputTokens`
- `output_tokens`: `output.outputBodyJson.usage.outputTokens`
- `latency_ms`: `output.outputBodyJson.metrics.latencyMs`

**Note**: `agent_name` is extracted from the IAM execution role ARN. Falls back to model family (e.g., `claude-sonnet`) if not an AgentCore Runtime invocation.

---

## 2. Staging Parquet

**Location**: `s3://bucket/staging/agent_name={agent}/date={date}/`
**Format**: Apache Parquet (17 columns)
**Schema**: See `cdk/lambda/transform_bedrock_logs/schema.py` (lines 21-50)

**Columns**:
```python
1.  timestamp (timestamp[ms, UTC])
2.  request_id (string)
3.  agent_name (string) - extracted from identity.arn (AgentCore Runtime name)
4.  model_id (string)
5.  region (string)
6.  prompt (string)
7.  system_prompt (string)
8.  response (string)
9.  stop_reason (string)
10. finish_reason (string)
11. input_tokens (int64)
12. output_tokens (int64)
13. total_tokens (int64)
14. latency_ms (int64)
15. error_message (string)
16. _agent_name (string) - partition key
17. _date (string) - partition key (YYYY-MM-DD)
```

**Example Record**:
```python
{
    "timestamp": "2025-11-25T13:10:36.000Z",
    "request_id": "73ecc88e-d2a5-44ef-acae-f13cfb0e5a56",
    "agent_name": "finance_personal_assistant",
    "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "region": "us-west-2",
    "prompt": "Hello, are you operational?",
    "system_prompt": "You are a financial advisor...",
    "response": "¡Hola! Yes, I'm fully operational...",
    "stop_reason": "end_turn",
    "finish_reason": "",
    "input_tokens": 1959,
    "output_tokens": 89,
    "total_tokens": 2048,
    "latency_ms": 3176,
    "error_message": "",
    "_agent_name": "finance_personal_assistant",
    "_date": "2025-11-25"
}
```

---

## 3. Evaluation JSONL

**Location**: `s3://bucket/evaluation-datasets/{agent}/{timestamp}/dataset.jsonl`
**Format**: JSONL (newline-delimited JSON)
**Specification**: Bedrock Model Evaluation API format

**Schema**:
```json
{
  "prompt": "string (required)",
  "modelResponses": [
    {
      "response": "string (required)",
      "modelIdentifier": "string (required)"
    }
  ],
  "category": "string (optional)",
  "referenceResponse": "string (optional)"
}
```

**Example Record**:
```json
{
  "prompt": "Hello, are you operational?",
  "modelResponses": [{
    "response": "¡Hola! Yes, I'm fully operational...",
    "modelIdentifier": "finance_personal_assistant"
  }]
}
```

**Transformation** (implemented in `cdk/lambda/filter_gather_data/lambda_function.py`):
```python
# Staging → Evaluation
{
    "prompt": record["prompt"],
    "modelResponses": [{
        "response": record["response"],
        "modelIdentifier": record["agent_name"]
    }]
}
```

---

## Schema Evolution

**To update schemas:**

1. **Bedrock Log changes**: Update extraction logic in `transform_bedrock_logs/schema.py`
2. **Parquet schema changes**: Update `BEDROCK_LOG_SCHEMA` in `schema.py` + redeploy Transform Lambda
3. **JSONL changes**: Update `transform_to_bedrock_format()` in `filter_gather_data/lambda_function.py`
4. **Documentation**: Update this file (single source of truth)

**Version tracking**: Document changes in git commit messages with schema migration notes.
