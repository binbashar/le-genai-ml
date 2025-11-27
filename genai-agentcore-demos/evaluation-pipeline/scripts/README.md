# Evaluation Pipeline Scripts

Utility scripts for testing and analyzing the evaluation pipeline.

## Available Scripts

### `analyze_bedrock_logs.py`
Analyze Bedrock model invocation logs stored in S3.

**Usage:**
```bash
# Search for specific prompts
uv run scripts/analyze_bedrock_logs.py search "Hello world" \
  --bucket bb-bedrock-invocations-ab4d1c24 \
  --hours 24

# Analyze conversation flow
uv run scripts/analyze_bedrock_logs.py conversation \
  --bucket bb-bedrock-invocations-ab4d1c24 \
  --hours 6

# View log structure
uv run scripts/analyze_bedrock_logs.py structure \
  --bucket bb-bedrock-invocations-ab4d1c24
```

**Commands:**
- `search <term>` - Search for prompts containing a specific term
- `conversation` - Analyze conversation flow and history
- `structure` - Print log structure documentation with sample record

**Options:**
- `--bucket` (required) - S3 bucket containing Bedrock logs
- `--profile` - AWS profile (default: binbash)
- `--region` - AWS region (default: us-west-2)
- `--hours` - Hours back to search (default: 24)
- `--max-results` - Max search results (default: 10)

**What it does:**
- Parses JSONL log files (gzipped or plain)
- Extracts user prompts and assistant responses
- Shows token usage and latency metrics
- Removes memory context noise from prompts

---

### `run_evaluation.py`
Run evaluation pipeline from YAML configuration file.

**Usage:**
```bash
# Start evaluation (async)
uv run scripts/run_evaluation.py config/runs/example.yaml

# Start and wait for completion
uv run scripts/run_evaluation.py config/runs/example.yaml --wait

# With region override
uv run scripts/run_evaluation.py config/runs/example.yaml --region us-east-1
```

**Options:**
- `config_file` (required) - Path to YAML configuration file
- `--wait` - Wait for execution to complete
- `--region` - AWS region (default: us-west-2)

**What it does:**
- Validates YAML configuration against schema
- Retrieves Step Functions ARN from CloudFormation
- Starts Step Functions execution with config
- Optionally polls until completion

---

### `run_evaluation.sh`
Convenience wrapper for `run_evaluation.py` with default AWS profile.

**Usage:**
```bash
./scripts/run_evaluation.sh config/runs/example.yaml
./scripts/run_evaluation.sh config/runs/example.yaml --wait
```

**Environment:**
- Sets `AWS_PROFILE=binbash` by default
- Forwards all arguments to `run_evaluation.py`

---

### `test_01_data_flow.sh`
End-to-end data flow validation test for Phase 1 of the pipeline.

**Usage:**
```bash
./scripts/test_01_data_flow.sh
```

**Environment variables:**
- `AGENT_ARN` - Agent ARN to test (default: finance_personal_assistant)
- `AWS_ACCOUNT_ID` - AWS account ID
- `AWS_REGION` - AWS region (default: us-west-2)

**What it tests:**
1. Invokes agent with test prompt
2. Verifies CloudWatch Logs capture
3. Waits for Firehose buffer flush (90s)
4. Checks S3 for new files in `raw/` prefix
5. Downloads and decompresses latest file
6. Validates Bedrock log structure (modelId, input, output, timestamp)

**Exit codes:**
- `0` - All validations passed
- `1` - One or more validations failed

---

## Prerequisites

- AWS credentials configured (`AWS_PROFILE=binbash`)
- Evaluation pipeline infrastructure deployed
- `uv` package manager installed

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Pipeline overview and architecture
- [SCHEMAS.md](../SCHEMAS.md) - Data format specifications
