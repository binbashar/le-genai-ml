# Schemas - Canonical Reference

**Single source of truth for all data schemas in the evaluation pipeline.**

## Data Flow

```
Bedrock Log (JSON) → Staging Parquet (18 cols) → Evaluation JSONL (2 fields)
```

---

## Date Format Specification

### Input Dates (Step Function Parameters)

- **Accepted formats** (all UTC):
  - Date only: `YYYY-MM-DD` → normalized to `00:00:00Z` / `23:59:59Z`
  - Hour:minute: `YYYY-MM-DDTHH:MMZ` → normalized to `HH:MM:00Z`
  - Full ISO 8601: `YYYY-MM-DDTHH:MM:SSZ` → unchanged
- **Range**: Both `start_date` and `end_date` are **inclusive**

### Examples

```json
{"start_date": "2025-11-25", "end_date": "2025-11-25"}
{"start_date": "2025-11-25T09:00Z", "end_date": "2025-11-25T17:00Z"}
{"start_date": "2025-11-25T09:30:00Z", "end_date": "2025-11-25T17:45:00Z"}
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

**Location**: `s3://bucket/staging/agent_name={agent}/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/`
**Format**: Apache Parquet (18 columns)
**Schema**: See `cdk/lambda/transform_bedrock_logs/schema.py`

**Columns**:
```
1-5.   timestamp, request_id, agent_name, model_id, region
6-7.   prompt, system_prompt
8-10.  response, stop_reason, finish_reason
11-14. input_tokens, output_tokens, total_tokens, latency_ms
15.    error_message
16-18. _agent_name, _date (YYYY-MM-DD), _hour (HH)  ← partition keys
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
