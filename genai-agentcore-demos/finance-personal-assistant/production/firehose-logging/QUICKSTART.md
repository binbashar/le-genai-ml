# Quick Start

## Setup Firehose Logging

```bash
./setup.sh
```

This automatically:
- ✅ Checks if agent is deployed
- ✅ Verifies AWS credentials
- ✅ Installs Python dependencies
- ✅ Creates all resources (S3, Firehose, IAM, subscription filter)

## Verify It Works

### 1. Generate logs
```bash
cd .. && ./health.sh
```

### 2. Wait ~60 seconds, then check S3
```bash
aws s3 ls s3://finance_personal_assistant-logs-905418344519-us-west-2/logs/ --recursive
```

### 3. Download and view a log file
```bash
aws s3 cp s3://finance_personal_assistant-logs-905418344519-us-west-2/logs/year=2025/month=11/day=21/filename.gz - | gunzip | jq
```

## Cleanup

```bash
./cleanup.sh
```

**Warning**: Deletes S3 bucket and all logs!

## Troubleshooting

**No logs in S3?**
- Wait at least 60 seconds (Firehose buffers for 5MB or 60 seconds)
- Check CloudWatch Logs directly: `aws logs tail /aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE`
- Check Firehose errors: `aws logs tail /aws/kinesisfirehose/finance_personal_assistant-logs`

**Setup fails?**
- Ensure agent is deployed: `cd .. && ./launch.sh`
- Check AWS credentials: `aws sts get-caller-identity`

## What Gets Created

| Resource | Name |
|----------|------|
| S3 Bucket | `finance_personal_assistant-logs-{account}-{region}` |
| Firehose Stream | `finance_personal_assistant-logs` |
| Subscription Filter | `finance_personal_assistant-to-firehose` |
| IAM Role (Firehose) | `finance_personal_assistant-firehose-role` |
| IAM Role (CloudWatch) | `finance_personal_assistant-logs-to-firehose-role` |

## Log Structure

```
s3://finance_personal_assistant-logs-{account}-{region}/
  logs/
    year=2025/
      month=11/
        day=21/
          file1.gz (GZIP-compressed JSON)
          file2.gz
  errors/  (if any Firehose delivery failures)
```

## Cost

~$1.56/month for 1 GB/day of logs:
- Firehose: $0.87/month ($0.029/GB ingested)
- S3 storage: $0.69/month ($0.023/GB/month)

See [README.md](README.md) for full documentation.
