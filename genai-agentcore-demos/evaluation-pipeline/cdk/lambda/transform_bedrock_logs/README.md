# Bedrock Log Transformation Lambda

Docker-based Lambda function for transforming Bedrock invocation logs via Kinesis Firehose.

## Purpose

This Lambda function is invoked by Kinesis Firehose to:
1. **Parse CloudWatch Logs format** (gzip-compressed JSON)
2. **Extract Bedrock invocation logs** (prompt, response, tokens, metadata)
3. **Apply PII scrubbing** (basic regex patterns for MVP)
4. **Transform to structured Parquet schema** (17 columns for Athena queries)
5. **Write Parquet directly to S3** (Lambda manages directory structure and incremental storage)
6. **Return "Dropped" to Firehose** (records already written by Lambda)

## Architecture

```
CloudWatch Logs → Firehose → Lambda (transform + S3 write) → S3 (staging/)
                                ↓
                            Parquet files with partitioning
```

**Key Design:** Lambda writes Parquet files directly to S3 (bypasses Firehose for writes) to have full control over:
- **Directory structure**: `staging/agent_name=*/date=*/part-YYYYMMDD-HHMMSS-*.parquet`
- **Parquet file management**: Incremental storage with timestamp-based filenames
- **Partition grouping**: Batches records by partition key before writing
- **Compression**: Snappy compression (good balance of speed/size)

## Files

- **`lambda_function.py`**: Main handler for Firehose transformation
- **`pii_scrubber.py`**: Basic regex-based PII detection (SSN, email, phone, credit card)
- **`schema.py`**: Parquet schema definition (17 columns)
- **`parquet_storage.py`**: S3/Parquet management with incremental writes
- **`Dockerfile`**: Python 3.13 + uv dependencies
- **`pyproject.toml`**: Dependencies (PyArrow, boto3)

## PII Scrubbing (MVP)

Current implementation uses **basic regex patterns**:
- SSN: `\d{3}-\d{2}-\d{4}` → `[SSN_REDACTED]`
- Email: `user@example.com` → `[EMAIL_REDACTED]`
- Phone: `(555) 123-4567` → `[PHONE_REDACTED]`
- Credit Card: `1234-5678-9012-3456` → `[CC_REDACTED]`

**Post-MVP enhancements**:
- AWS Bedrock Guardrails (ML-based PII detection)
- AWS Comprehend (entity recognition)

## Parquet Schema (17 Columns)

### Metadata (5)
- `timestamp`: Invocation timestamp (UTC)
- `request_id`: Unique request identifier
- `agent_name`: Extracted from model ID
- `model_id`: Full Bedrock model ID or inference profile
- `region`: AWS region

### Input (2)
- `prompt`: User message (PII scrubbed)
- `system_prompt`: System instructions

### Output (3)
- `response`: Agent response (PII scrubbed)
- `stop_reason`: Why generation stopped
- `finish_reason`: Completion status

### Token Metrics (4)
- `input_tokens`: Input token count
- `output_tokens`: Output token count
- `total_tokens`: Sum of input + output
- `latency_ms`: Response time in milliseconds

### Error Handling (1)
- `error_message`: Error details (if invocation failed)

### Partitioning (2)
- `_agent_name`: For Athena partition pruning
- `_date`: Date partition (YYYY-MM-DD)

## Local Testing

Not yet implemented. See Phase 2 test plan in `../../../PLAN.md`.

## Deployment

Deployed automatically via CDK when `enable_transformation=true` (default):

```bash
cd ../../
./deploy.sh  # Builds Docker image and deploys Lambda
```

## Monitoring

- **Lambda Logs**: `/aws/lambda/evaluation-pipeline-transform-bedrock-logs`
- **Firehose Logs**: `/aws/kinesisfirehose/evaluation-pipeline`
- **Timeout**: 3 minutes (Firehose maximum)
- **Memory**: 512 MB
- **Retries**: 2 attempts

## Dependencies

- **PyArrow** ≥18.1.0 (Parquet file creation and schema)
- **boto3** ≥1.34.0 (S3 client for writing Parquet files)
- Python 3.13 (AWS Lambda runtime)
- uv (Rust-based package manager)

## Incremental Storage Strategy

The Lambda function creates **new Parquet files** for each batch of records:
- Filename format: `part-YYYYMMDD-HHMMSS-microseconds.parquet`
- No appending to existing files (Parquet doesn't support efficient appends)
- Each invocation creates independent files within partitions
- Athena reads all files in a partition automatically

**Example S3 structure:**
```
s3://bucket/staging/
├── agent_name=nova-lite/
│   └── date=2025-11-24/
│       ├── part-20251124-120000-123456.parquet (100 records)
│       ├── part-20251124-120100-234567.parquet (150 records)
│       └── part-20251124-120200-345678.parquet (200 records)
└── agent_name=claude-sonnet/
    └── date=2025-11-24/
        └── part-20251124-120000-456789.parquet (50 records)
```

## Environment Variables

- **`BUCKET_NAME`**: S3 bucket name (set by CDK, e.g., `eval-pipeline-905418344519-us-west-2`)
- **`LOG_LEVEL`**: Logging level (default: `INFO`)
- **`PYTHONUNBUFFERED`**: Unbuffered logging for CloudWatch

## Future Enhancements

1. **Advanced PII detection** (Bedrock Guardrails, Comprehend)
2. **Parquet file compaction** (merge small files periodically)
3. **Unit tests** (`test_lambda_function.py`, `test_parquet_storage.py`)
4. **Local testing script** (`test_local.py`)
5. **Performance metrics** (CloudWatch custom metrics)
6. **Batch optimization** (adjust memory/timeout based on throughput)
