# Create Evaluation Job Lambda

**Status**: ✅ Validated (2025-11-25)

Creates AWS Bedrock model evaluation jobs using the filtered dataset from the previous pipeline step.

## Overview

This Lambda is part of the evaluation pipeline's Step Functions workflow:

```
Filter/Gather Data → Create Evaluation Job → Poll Job Status → Process Results
                     ^^^^^^^^^^^^^^^^^^^^^
                     (This Lambda)
```

## Input/Output

### Input (from Step Functions)

```json
{
  "dataset_s3_uri": "s3://bucket/evaluation-datasets/agent/timestamp/dataset.jsonl",
  "question_count": 95,
  "agent_name": "finance-personal-assistant",
  "metrics": ["Builtin.Correctness"],
  "output_s3_uri": "s3://bucket/evaluation-results/agent/timestamp/"
}
```

### Output (to Step Functions)

```json
{
  "job_arn": "arn:aws:bedrock:us-west-2:123456789012:evaluation-job/abc123",
  "job_name": "eval-finance-personal-assistant-20251125-120000",
  "status": "InProgress",
  "dataset_s3_uri": "s3://...",
  "output_s3_uri": "s3://...",
  "question_count": 10,
  "metrics": ["Builtin.Correctness"],
  "judge_model_id": "us.amazon.nova-pro-v1:0"
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STAGING_BUCKET` | Yes* | - | S3 bucket for evaluation data (*if output_s3_uri not in event) |
| `EVALUATION_ROLE_ARN` | Yes | - | IAM role ARN for Bedrock evaluation jobs |
| `JUDGE_MODEL_ID` | No | `us.amazon.nova-pro-v1:0` | Model ID for judge (evaluator) |
| `MAX_EVALUATION_SAMPLES` | No | `10` | Maximum samples per evaluation (MVP limit) |

## Bedrock Evaluation Configuration

### Metrics

Default metric for MVP: `Builtin.Correctness`

Available built-in metrics:
- `Builtin.Correctness` - Evaluates factual accuracy
- `Builtin.Completeness` - Evaluates response completeness
- `Builtin.Helpfulness` - Evaluates how helpful the response is
- `Builtin.Harmlessness` - Evaluates safety of response

### Judge Model

Default: Amazon Nova Pro (`us.amazon.nova-pro-v1:0`)

Chosen for:
- Cost-effective for testing
- Fast inference
- Good evaluation quality

### Inference Source

Uses **precomputed inference** mode because:
- Agent responses already exist in the dataset
- No need to re-invoke the model
- Faster and cheaper evaluation

## IAM Permissions

The Lambda execution role requires:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:CreateEvaluationJob"
  ],
  "Resource": "*"
}
```

The evaluation job role (`EVALUATION_ROLE_ARN`) requires:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:bedrock:*::foundation-model/*",
    "arn:aws:s3:::your-bucket/*"
  ]
}
```

## Local Testing

```bash
# Set environment variables
export STAGING_BUCKET="eval-pipeline-905418344519-us-west-2"
export EVALUATION_ROLE_ARN="arn:aws:iam::905418344519:role/EvaluationPipelineJobRole"
export JUDGE_MODEL_ID="us.amazon.nova-pro-v1:0"
export MAX_EVALUATION_SAMPLES="10"

# Test with sample event
python3 -c "
import json
from lambda_function import lambda_handler

event = {
    'dataset_s3_uri': 's3://eval-pipeline-905418344519-us-west-2/evaluation-datasets/test/dataset.jsonl',
    'question_count': 5,
    'agent_name': 'test-agent',
    'metrics': ['Builtin.Correctness']
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
"
```

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ValidationException` | Invalid configuration | Check dataset format, metrics, model IDs |
| `ServiceQuotaExceededException` | Too many concurrent jobs | Wait and retry, or request quota increase |
| `ConflictException` | Job name exists | Names are timestamped, should be unique |
| `AccessDeniedException` | IAM issues | Check Lambda and evaluation role permissions |

## Cost Considerations

**MVP Testing (max 10 samples):**
- Nova Pro judge: ~$0.001 per sample
- Total: ~$0.01 per evaluation run

**Production (100+ samples):**
- Increase `MAX_EVALUATION_SAMPLES`
- Consider batching by date ranges
- Monitor Bedrock evaluation job costs

## References

- [AWS Bedrock CreateEvaluationJob API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_CreateEvaluationJob.html)
- [Model evaluation built-in metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-built-in-metrics.html)
- [Evaluation job permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-security.html)
