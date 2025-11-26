# Evaluation Pipeline

Automated evaluation pipeline for AWS Bedrock AgentCore agents using LLM-as-a-judge metrics.

**Status**: 95% Complete | [Full Specifications →](PRD.md)

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

# Deploy all stacks
uv run cdk deploy --all \
  -c deploy_filter_lambda=true \
  -c deploy_evaluation_job=true \
  -c deploy_orchestration=true \
  --require-approval never
```

## Running Evaluations

Three ways to run evaluations:

### Option 1: YAML Configuration (Recommended)

```bash
# Run evaluation
./scripts/run_evaluation.sh config/runs/example.yaml

# Run and wait for results
./scripts/run_evaluation.sh config/runs/example.yaml --wait
```

### Option 2: AWS CLI Direct

```bash
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name EvaluationPipelineOrchestration \
  --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
  --output text)

aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"agent_name":"finance_personal_assistant","start_date":"2025-11-25","end_date":"2025-11-25","limit":10,"metrics":["Builtin.Correctness"]}'
```

### Option 3: Web UI

```bash
cd ui && npm install && npm run dev
# Open http://localhost:3000
```

## YAML Configuration

Create a config file in `config/runs/`:

```yaml
# Agent to evaluate (matches agent_name in S3 staging data)
agent_name: "finance_personal_assistant"

# Date/time range (ISO 8601 UTC)
start_date: "2025-11-25"           # Full day
end_date: "2025-11-25"

# Or with specific hours
start_date: "2025-11-25T09:00:00Z" # 9am UTC
end_date: "2025-11-25T17:00:00Z"   # 5pm UTC

# Max records to evaluate (1-100)
limit: 50

# Metrics to calculate
metrics:
  - "Builtin.Correctness"
  - "Builtin.Completeness"
```

### Filter Examples

**Single day:**
```yaml
agent_name: "finance_personal_assistant"
start_date: "2025-11-25"
end_date: "2025-11-25"
limit: 10
metrics: ["Builtin.Correctness"]
```

**Date range (week):**
```yaml
agent_name: "finance_personal_assistant"
start_date: "2025-11-18"
end_date: "2025-11-25"
limit: 100
metrics: ["Builtin.Correctness", "Builtin.Completeness"]
```

**Specific hours (business hours only):**
```yaml
agent_name: "finance_personal_assistant"
start_date: "2025-11-25T14:00:00Z"  # 2pm UTC
end_date: "2025-11-25T18:00:00Z"    # 6pm UTC
limit: 20
metrics: ["Builtin.Correctness"]
```

**Different agent:**
```yaml
agent_name: "claude-sonnet"  # Non-AgentCore invocations
start_date: "2025-11-25"
end_date: "2025-11-25"
limit: 50
metrics: ["Builtin.Harmfulness"]
```

## Available Metrics

| Metric | Description |
|--------|-------------|
| `Builtin.Correctness` | Factual accuracy |
| `Builtin.Completeness` | Response thoroughness |
| `Builtin.Helpfulness` | Usefulness to user |
| `Builtin.Harmfulness` | Harmful content detection |
| `Builtin.Stereotyping` | Bias detection |
| `Builtin.Refusal` | Appropriate refusals |

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
├── README.md              # This file
├── PRD.md                 # Specifications & requirements
├── SCHEMAS.md             # Data format reference
├── cdk/                   # Infrastructure as Code
│   └── lambda/            # Lambda functions (5)
├── scripts/               # CLI utilities
│   └── run_evaluation.sh  # Run from YAML config
├── config/runs/           # YAML evaluation configs
└── ui/                    # Next.js web interface
```

## Documentation

| Document | Purpose |
|----------|---------|
| [PRD.md](PRD.md) | Requirements & architecture |
| [SCHEMAS.md](SCHEMAS.md) | Data format reference |
| [ui/README.md](ui/README.md) | Web UI setup & troubleshooting |

## Cost

~$0.20/month with weekly evaluations (10% sampling, 100 questions)

See [PRD.md §7](PRD.md#7-cost-optimization) for detailed breakdown.

## License

Apache License 2.0 - See parent project LICENSE
