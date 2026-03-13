# Filter and Gather Data Lambda

Reads Parquet files from S3 staging, applies sampling, and generates JSONL datasets in Bedrock evaluation format.

## Function

**Input** (from Step Functions):
```json
{
  "agent_name": "my-agent",
  "start_date": "2025-11-25",
  "end_date": "2025-11-25",
  "limit": 10,
  "metrics": ["Builtin.Correctness"]
}
```

**Output** (to Step Functions):
```json
{
  "dataset_s3_uri": "s3://bucket/evaluation-datasets/my-agent/20251125-120000/dataset.jsonl",
  "question_count": 3,
  "sampling_stats": {
    "total_records": 10,
    "filtered_records": 10,
    "sampled_records": 3,
    "timestamp": "20251125-120000"
  }
}
```

## Schema Transformation

**Staging Parquet** → **Bedrock Evaluation JSONL**

Input:
```python
{
    "prompt": "<retrieved_memories>...\n\nUser: Hello, are you operational?",
    "response": "¡Hola! Yes, I'm fully operational...",
    "agent_name": "my-agent",
    "model_id": "us.anthropic.claude-sonnet-4-5",
    # ... 13 other fields
}
```

Output:
```json
{
  "prompt": "Hello, are you operational?",
  "modelResponses": [{
    "response": "¡Hola! Yes, I'm fully operational...",
    "modelIdentifier": "my-agent"
  }]
}
```

## Environment

- `STAGING_BUCKET` - S3 bucket name (required)

## Configuration

- **Runtime**: Python 3.13 (Docker)
- **Memory**: 1024MB
- **Timeout**: 300s
- **Deployment**: CDK with Docker image build
