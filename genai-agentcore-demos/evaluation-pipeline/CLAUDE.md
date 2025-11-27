# Evaluation Pipeline

Automated evaluation pipeline for AWS Bedrock AgentCore agents using LLM-as-a-judge metrics.

**Status**: Complete | **Last Validated**: 2025-11-25

## Quick Start

```bash
# Deploy infrastructure
cd cdk
export AWS_PROFILE=binbash
uv run cdk deploy EvaluationPipeline --require-approval never

# After deployment, configure Bedrock logging (one-time):
# Run the command from ManualConfigCommand output

# Run evaluation via CLI
aws stepfunctions start-execution \
  --state-machine-arn $(aws cloudformation describe-stacks --stack-name EvaluationPipeline --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' --output text) \
  --input '{"agent_name":"finance_personal_assistant","start_date":"2025-11-25","end_date":"2025-11-25","limit":10,"metrics":["Builtin.Correctness"]}'

# Or use Web UI
cd ui && npm install && npm run dev
# Open http://localhost:3000
```

## Architecture

```
AgentCore Agent → Bedrock → CloudWatch → Firehose → Transform Lambda → S3 Parquet
                                                                            ↓
                        Bedrock Eval ← JSONL ← Filter Lambda ← Step Functions (on-demand)
```

**Data flow:**
1. **Continuous ingestion**: Bedrock logs → CloudWatch (7-day) → Firehose → Transform Lambda → Parquet in S3
2. **On-demand evaluation**: Step Functions triggers Filter → CreateEvalJob → Poll → ProcessResults (~8 min)

## Key Concepts

### Agent Name Extraction
Agent names are extracted from the IAM execution role ARN in Bedrock logs:
```
identity.arn: "arn:aws:sts::ACCOUNT:assumed-role/BedrockAgentCore-{agent_name}-execution-role/..."
```
Falls back to model family (e.g., `claude-sonnet`) for non-AgentCore invocations.

**Important:** Agents must use named IAM roles following this pattern. See [README.md Prerequisites](README.md#prerequisites) for setup instructions and reference implementations.

### S3 Structure
```
s3://eval-pipeline-{account}-{region}/
├── staging/agent_name={name}/date={YYYY-MM-DD}/*.parquet
├── evaluation-datasets/{agent}/{timestamp}/dataset.jsonl
└── evaluation-results/{agent}/{run-id}/
```

## Files

| Path | Purpose |
|------|---------|
| `cdk/` | CDK infrastructure (4 stacks) |
| `cdk/lambda/transform_bedrock_logs/` | Firehose → Parquet (PII scrubbing) |
| `cdk/lambda/filter_gather_data/` | Parquet → JSONL |
| `cdk/lambda/create_evaluation_job/` | Bedrock CreateEvaluationJob API |
| `cdk/lambda/poll_job_status/` | Job status polling |
| `cdk/lambda/process_results/` | Results aggregation |
| `ui/` | Next.js web interface |
| `SCHEMAS.md` | Data format reference |

## Common Commands

```bash
# View logs
aws logs tail /aws/lambda/evaluation-pipeline-transform-bedrock-logs --follow

# Check S3 data
aws s3 ls s3://eval-pipeline-{account}-{region}/staging/ --recursive

# Monitor execution
aws stepfunctions describe-execution --execution-arn <arn>

# Get results
aws s3 cp s3://eval-pipeline-{account}-{region}/evaluation-results/{agent}/{run-id}/ . --recursive
```

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| `Builtin.Correctness` | Factual accuracy |
| `Builtin.Completeness` | Response thoroughness |
| `Builtin.Helpfulness` | Usefulness to user |
| `Builtin.Harmfulness` | Harmful content detection |

## Schema Reference

See [SCHEMAS.md](SCHEMAS.md) for complete data format specifications:
- Bedrock log JSON structure
- Parquet schema (17 columns)
- Evaluation JSONL format
