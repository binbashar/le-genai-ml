# Evaluation Pipeline

Automated evaluation pipeline for AWS Bedrock AgentCore agents using LLM-as-a-judge metrics.

**Status**: 90% Complete | [Full Specifications →](PRD.md)

## Architecture

```
Agent → Bedrock → CloudWatch → Firehose → Transform Lambda → Parquet → Filter Lambda → JSONL → Bedrock Evaluation
         (logs)    (7-day)     (buffer)    (PII scrub)      (staging)   (sample)    (dataset)    (metrics)
```

## Quick Start

### Prerequisites

```bash
export AWS_PROFILE=binbash
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-west-2
```

### Deploy

```bash
cd cdk

# Data pipeline (CloudWatch → Firehose → Lambda → S3)
uv run cdk deploy EvaluationPipeline

# Filter Lambda (Parquet → JSONL)
uv run cdk deploy EvaluationPipelineFilterLambda -c deploy_filter_lambda=true

# Evaluation Job Lambda (Bedrock API)
uv run cdk deploy EvaluationPipelineEvaluationJob -c deploy_evaluation_job=true
```

### Test Filter Lambda

```bash
FUNC=$(aws cloudformation describe-stacks \
  --stack-name EvaluationPipelineFilterLambda \
  --query 'Stacks[0].Outputs[?OutputKey==`FilterLambdaName`].OutputValue' \
  --output text)

# ISO 8601 UTC format (recommended)
aws lambda invoke --function-name $FUNC \
  --cli-binary-format raw-in-base64-out \
  --payload '{"agent_name":"claude-sonnet","start_date":"2025-11-25T00:00:00Z","end_date":"2025-11-25T23:59:59Z","limit":10,"metrics":["Builtin.Correctness"]}' \
  response.json && cat response.json | jq .

# Date-only format (backward compatible, normalized to full day UTC range)
aws lambda invoke --function-name $FUNC \
  --cli-binary-format raw-in-base64-out \
  --payload '{"agent_name":"claude-sonnet","start_date":"2025-11-25","end_date":"2025-11-25","limit":10,"metrics":["Builtin.Correctness"]}' \
  response.json && cat response.json | jq .
```

## Current Status

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | Data Collection (CloudWatch → Firehose → S3) | ✅ Complete |
| 2 | Transform Lambda (PII scrub → Parquet) | ✅ Complete |
| 4a | Filter Lambda (Parquet → JSONL) | ✅ Complete |
| 4b | Evaluation Job Lambda | ✅ Complete |
| 5 | Step Functions Orchestration | ✅ Complete |
| 6 | Production Hardening | 🟡 Next |

**Next**: Add EventBridge scheduling, improve metrics parsing, add alerts

## Project Structure

```
evaluation-pipeline/
├── README.md           # This file
├── PRD.md              # Specifications & requirements
├── SCHEMAS.md          # Data format reference
├── CLAUDE.md           # AI assistant context
├── cdk/                # Infrastructure as Code
│   ├── app.py          # CDK entry point
│   ├── stacks/         # Stack definitions
│   └── lambda/         # Lambda functions
│       ├── transform_bedrock_logs/
│       ├── filter_gather_data/
│       └── create_evaluation_job/
├── config/             # Configuration templates
└── docs/               # Additional documentation
```

## Documentation

| Document | Purpose |
|----------|---------|
| [PRD.md](PRD.md) | Requirements, architecture, specifications |
| [SCHEMAS.md](SCHEMAS.md) | Data format reference |
| [cdk/README.md](cdk/README.md) | CDK deployment guide |

## Cost

~$0.20/month with weekly evaluations (10% sampling, 100 questions)

See [PRD.md §7](PRD.md#7-cost-optimization) for detailed breakdown.

## License

Apache License 2.0 - See parent project LICENSE
