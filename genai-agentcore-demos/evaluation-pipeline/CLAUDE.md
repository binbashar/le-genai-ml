# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated evaluation pipeline for AWS Bedrock AgentCore agents using LLM-as-a-judge metrics. The pipeline captures Bedrock invocation logs, applies PII scrubbing, and runs on-demand evaluations via Step Functions.

## Quick Reference

```bash
# Deploy infrastructure
cd cdk && uv run cdk deploy EvaluationPipeline --require-approval never

# After deployment, configure Bedrock logging (one-time, from ManualConfigCommand output)
aws bedrock put-model-invocation-logging-configuration \
  --logging-config '{"cloudWatchConfig": {"logGroupName": "bedrock-model-invocations", "roleArn": "<role-arn>"}}'

# Run Model evaluation (from CloudWatch logs)
./scripts/run_evaluation.sh config/runs/example.yaml --wait

# Run RAG evaluation (from JSONL dataset)
./scripts/run_evaluation.sh config/runs/rag_example.yaml --wait                # Retrieve + Generate
./scripts/run_evaluation.sh config/runs/rag_retrieve_only_example.yaml --wait  # Retrieve only

# Run Web UI
cd ui && npm install && npm run dev  # http://localhost:3000

# Deploy without Bedrock Guardrails (regex-only PII)
cd cdk && uv run cdk deploy EvaluationPipeline -c deploy_guardrails=false
```

## Architecture

```
Data Collection (continuous):
  Bedrock → CloudWatch (7-day) → Firehose → Transform Lambda → S3 Parquet

Evaluation (on-demand via Step Functions):
  Input → Filter Lambda → Create Eval Job → Poll Status → Process Results (~8 min)
```

**S3 Structure:**
```
s3://eval-pipeline-{account}-{region}/
├── staging/agent_name={name}/yyyy=YYYY/mm=MM/dd=DD/hh=HH/*.parquet
├── evaluation-datasets/{agent}/{timestamp}/dataset.jsonl
└── evaluation-results/{agent}/{run-id}/
```

## Development Commands

### CDK Infrastructure

```bash
cd cdk

# Install dependencies
uv sync

# Synthesize CloudFormation
uv run cdk synth

# Deploy (full stack)
uv run cdk deploy EvaluationPipeline --require-approval never

# Deploy without orchestration (data collection only)
uv run cdk deploy EvaluationPipeline -c deploy_orchestration=false

# Diff changes
uv run cdk diff EvaluationPipeline

# Destroy stack
uv run cdk destroy EvaluationPipeline
```

### Lambda Development

Each Lambda has its own directory with `pyproject.toml`:
- `cdk/lambda/transform_bedrock_logs/` - Firehose → Parquet (PII scrubbing)
- `cdk/lambda/filter_gather_data/` - Parquet → JSONL (Docker-based)
- `cdk/lambda/create_evaluation_job/` - Bedrock CreateEvaluationJob API
- `cdk/lambda/poll_job_status/` - Job status polling
- `cdk/lambda/process_results/` - Results aggregation

```bash
# Install Lambda dependencies (transform_bedrock_logs example)
cd cdk/lambda/transform_bedrock_logs
uv sync

# Run tests locally (if available)
uv run python -m pytest

# View Lambda logs
aws logs tail /aws/lambda/evaluation-pipeline-transform-bedrock-logs --follow
aws logs tail /aws/lambda/EvaluationPipeline-FilterGatherDataLambda* --follow
```

### Web UI

```bash
cd ui

# Install dependencies
npm install

# Development server
npm run dev

# Lint
npm run lint

# Build for production
npm run build
```

### Monitoring & Debugging

```bash
# View transform Lambda logs
aws logs tail /aws/lambda/evaluation-pipeline-transform-bedrock-logs --follow

# Check S3 data
aws s3 ls s3://eval-pipeline-{account}-{region}/staging/ --recursive

# Monitor Step Functions execution
aws stepfunctions describe-execution --execution-arn <arn>

# Get evaluation results
aws s3 cp s3://eval-pipeline-{account}-{region}/evaluation-results/{agent}/{run-id}/ . --recursive

# List recent Firehose errors
aws s3 ls s3://eval-pipeline-{account}-{region}/staging-failed/ --recursive
```

## Key Concepts

### Agent Name Extraction

Agent names are extracted from the IAM execution role ARN in Bedrock logs:
```
identity.arn: "arn:aws:sts::ACCOUNT:assumed-role/BedrockAgentCore-{agent_name}-execution-role/..."
```
Agents must use named IAM roles following this pattern (`BedrockAgentCore-{name}-execution-role`). Falls back to model family (e.g., `claude-sonnet`) for non-AgentCore invocations.

### PII Filtering

Defense-in-depth approach with two layers:
1. **Regex-based** (fast, free): SSN, email, phone, credit card patterns
2. **Bedrock Guardrails** (ML-based): 30+ PII types with ANONYMIZE action

**Configuration via Lambda environment variables:**
- `GUARDRAILS_ENABLED`: Enable Bedrock Guardrails ML detection
- `PII_REGEX_ENABLED`: Enable regex-based scrubbing
- `GUARDRAIL_ID` / `GUARDRAIL_VERSION`: Guardrail identifiers

**Modes:**
| GUARDRAILS_ENABLED | PII_REGEX_ENABLED | Mode |
|--------------------|-------------------|------|
| true | true | Defense-in-depth (regex → Guardrails) |
| true | false | Guardrails only (isolated testing) |
| false | true | Regex only (free baseline) |
| false | false | Pass-through (no filtering) |

### Evaluation Types

| Type | Description | Data Source |
|------|-------------|-------------|
| `MODEL` | Evaluate LLM response quality | CloudWatch logs (Parquet) |
| `RAG_RETRIEVE_AND_GENERATE` | Evaluate retrieval + generation | JSONL dataset |
| `RAG_RETRIEVE_ONLY` | Evaluate retrieval quality only | JSONL dataset |

### Evaluation Metrics

**Model & RAG (Retrieve+Generate):**
| Metric | Description |
|--------|-------------|
| `Builtin.Correctness` | Factual accuracy |
| `Builtin.Completeness` | Response thoroughness |
| `Builtin.Helpfulness` | Usefulness to user |
| `Builtin.Harmfulness` | Harmful content detection |
| `Builtin.Stereotyping` | Bias detection |
| `Builtin.Refusal` | Appropriate refusals |

**RAG-Specific (Retrieve+Generate):**
| Metric | Description |
|--------|-------------|
| `Builtin.Faithfulness` | Is response grounded in chunks? |
| `Builtin.CitationPrecision` | Are citations correct? |
| `Builtin.CitationCoverage` | Is response supported by citations? |

**RAG-Specific (Retrieve Only):**
| Metric | Description |
|--------|-------------|
| `Builtin.ContextRelevance` | Are chunks relevant to query? |
| `Builtin.ContextCoverage` | Do chunks cover required info? |

See [docs/rag_evaluation.md](docs/rag_evaluation.md) for detailed RAG evaluation guide.

## Project Structure

```
evaluation-pipeline/
├── cdk/                          # CDK infrastructure
│   ├── app.py                    # CDK app entry point
│   ├── stacks/                   # Stack definitions
│   │   └── evaluation_pipeline_stack.py
│   └── lambda/                   # Lambda functions
│       ├── transform_bedrock_logs/   # Firehose → Parquet
│       │   ├── lambda_function.py
│       │   ├── schema.py             # Parquet schema definitions
│       │   ├── pii_scrubber.py       # PII filtering logic
│       │   └── parquet_storage.py    # S3 Parquet writer
│       ├── filter_gather_data/       # Parquet → JSONL (Docker)
│       ├── create_evaluation_job/
│       ├── poll_job_status/
│       └── process_results/
├── config/
│   ├── runs/                     # YAML evaluation configs
│   │   ├── example.yaml          # Model evaluation example
│   │   ├── rag_example.yaml      # RAG retrieve+generate example
│   │   └── rag_retrieve_only_example.yaml  # RAG retrieve-only example
│   ├── datasets/                 # Sample JSONL datasets for RAG
│   │   ├── rag_sample.jsonl
│   │   └── rag_retrieve_only_sample.jsonl
│   └── config_schema_mvp.py      # Config validation
├── scripts/
│   ├── run_evaluation.sh         # Run from YAML config
│   └── run_evaluation.py         # Python CLI
├── ui/                           # Next.js web interface
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   │   └── api/              # API routes (agents, experiments)
│   │   ├── components/           # React components
│   │   ├── hooks/                # Custom hooks (polling, agents)
│   │   └── lib/                  # AWS SDK, SSM, utilities
│   └── package.json
├── SCHEMAS.md                    # Data format reference
└── PRD.md                        # Specifications & requirements
```

## YAML Configuration

Create evaluation configs in `config/runs/`:

### Model Evaluation (from CloudWatch logs)

```yaml
agent_name: "finance_personal_assistant"
evaluation_type: "MODEL"  # Default, can be omitted

# Date range (ISO 8601, both inclusive)
start_date: "2025-11-25"
end_date: "2025-11-25"

limit: 50
metrics:
  - "Builtin.Correctness"
  - "Builtin.Completeness"
```

### RAG Evaluation (from JSONL dataset)

```yaml
agent_name: "finance_personal_assistant"
evaluation_type: "RAG_RETRIEVE_AND_GENERATE"  # or "RAG_RETRIEVE_ONLY"

# Local JSONL file (auto-uploaded to S3)
dataset_path: "config/datasets/rag_sample.jsonl"

limit: 10
metrics:
  - "Builtin.Faithfulness"
  - "Builtin.Correctness"
  - "Builtin.Completeness"
```

## Troubleshooting

**"No traces found" error:**
- Agent likely uses auto-created IAM role without required naming pattern
- Verify: `grep execution_role .bedrock_agentcore.yaml` should show `BedrockAgentCore-{agent_name}-execution-role`
- Check S3: `aws s3 ls s3://eval-pipeline-{account}-{region}/staging/` should show `agent_name=your_agent_name/`

**Transform Lambda failures:**
- Check logs: `aws logs tail /aws/lambda/evaluation-pipeline-transform-bedrock-logs --follow`
- Check Firehose error prefix: `aws s3 ls s3://eval-pipeline-{account}-{region}/staging-failed/`

**Web UI "No agents found":**
- Verify SSM parameters: `aws ssm get-parameters-by-path --path /agentcore/ --recursive`

## Schema Reference

See [SCHEMAS.md](SCHEMAS.md) for complete data format specifications:
- Bedrock log JSON structure and extraction paths
- Parquet schema (18 columns)
- Evaluation JSONL format
