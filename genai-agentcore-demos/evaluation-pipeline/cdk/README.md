# CDK Infrastructure

Infrastructure as Code for the Evaluation Pipeline.

## Quick Start

```bash
cd evaluation-pipeline/cdk
uv sync

export AWS_PROFILE=binbash
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-west-2

# Bootstrap (first time only)
uv run cdk bootstrap

# Deploy all stacks
uv run cdk deploy --all --require-approval never \
  -c deploy_filter_lambda=true \
  -c deploy_evaluation_job=true \
  -c deploy_orchestration=true
```

## Stacks

| Stack | Command | Status |
|-------|---------|--------|
| `EvaluationPipeline` | `cdk deploy EvaluationPipeline` | ✅ |
| `EvaluationPipelineFilterLambda` | `cdk deploy ... -c deploy_filter_lambda=true` | ✅ |
| `EvaluationPipelineEvaluationJob` | `cdk deploy ... -c deploy_evaluation_job=true` | ✅ |
| `EvaluationPipelineOrchestration` | `cdk deploy ... -c deploy_orchestration=true` | ✅ |

## Feature Flags

```bash
uv run cdk deploy -c enable_transformation=false  # Disable transform Lambda
uv run cdk deploy -c deploy_filter_lambda=true    # Enable filter Lambda stack
uv run cdk deploy -c deploy_evaluation_job=true   # Enable evaluation job stack
uv run cdk deploy -c deploy_orchestration=true    # Enable Step Functions orchestration
```

## Directory Structure

```
cdk/
├── app.py                          # Entry point
├── stacks/
│   ├── data_collection_stack.py    # Phase 1-2: CloudWatch → S3
│   ├── filter_lambda_stack.py      # Phase 4a: Parquet → JSONL
│   ├── evaluation_job_stack.py     # Phase 4b: Bedrock API
│   └── orchestration_stack.py      # Phase 5: Step Functions
└── lambda/
    ├── transform_bedrock_logs/     # Firehose transformation
    ├── filter_gather_data/         # Data filtering
    ├── create_evaluation_job/      # Evaluation jobs
    ├── poll_job_status/            # Job status polling
    └── process_results/            # Results aggregation
```

## Configure Bedrock Logging

After deployment, enable Bedrock model invocation logging:

```bash
./configure_logging.sh
```

## Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name EvaluationPipeline \
  --query 'Stacks[0].Outputs' \
  --output table
```

| Output | Description |
|--------|-------------|
| `LogGroupName` | CloudWatch log group |
| `BucketName` | S3 bucket for data |
| `FirehoseStreamName` | Firehose delivery stream |
| `BedrockLoggingRoleArn` | IAM role for Bedrock logging |

## Resources Created

### CloudWatch
- `bedrock-model-invocations` (7-day retention, account-wide)
- `/aws/kinesisfirehose/evaluation-pipeline` (Firehose logs)

### S3
- `eval-pipeline-{account}-{region}` (SSE-S3, private)

### Kinesis Firehose
- `evaluation-pipeline-cloudwatch-to-s3` (60s/1MB buffer, GZIP)

### Lambda Functions

| Function | Memory | Timeout | Packaging |
|----------|--------|---------|-----------|
| Transform | 512MB | 3min | Zip + bundling |
| Filter | 512MB | 5min | Docker |
| Evaluation Job | 256MB | 1min | Zip |

## Development

```bash
uv run cdk synth   # Generate CloudFormation
uv run cdk diff    # Show changes
uv run cdk deploy  # Deploy
uv run cdk destroy # Tear down
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `toolkit stack must be deployed` | `cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION` |
| `Bucket name already exists` | Change `bucket_name` in stack or delete existing |
| `not authorized to perform: iam:CreateRole` | Use admin credentials |

## References

- [PRD.md](../PRD.md) - Specifications and architecture
- [SCHEMAS.md](../SCHEMAS.md) - Data format reference
