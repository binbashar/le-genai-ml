# Firehose Logging for Finance Personal Assistant

Simple Python scripts to set up CloudWatch Logs → Firehose → S3 logging for the Finance Personal Assistant AgentCore agent.

## Why This Exists

By default, AgentCore Runtime logs go to CloudWatch Logs only. This setup:
- ✅ Archives logs to S3 for long-term storage
- ✅ Reduces CloudWatch Logs costs (S3 storage is much cheaper)
- ✅ Enables log analysis with tools like Athena, Glue, etc.
- ✅ Provides date-partitioned storage for easy querying

## Architecture

```
CloudWatch Log Group (/aws/bedrock-agentcore/runtimes/finance_personal_assistant-*)
    ↓
Subscription Filter (pushes logs to Firehose)
    ↓
Kinesis Data Firehose (buffers and compresses)
    ↓
S3 Bucket (finance_personal_assistant-logs-{account}-{region})
```

## Prerequisites

1. **Finance Personal Assistant must be deployed**:
   ```bash
   cd ..
   ./launch.sh
   ```

2. **AWS credentials configured**:
   ```bash
   export AWS_PROFILE=binbash
   aws sts get-caller-identity
   ```

3. **Python dependencies**:
   ```bash
   pip install boto3 pyyaml
   ```

## Setup

```bash
python3 setup_firehose.py
```

This creates:
- ✅ S3 bucket: `finance_personal_assistant-logs-{account}-{region}`
- ✅ Firehose delivery stream: `finance_personal_assistant-logs`
- ✅ IAM role for Firehose → S3
- ✅ IAM role for CloudWatch → Firehose
- ✅ Subscription filter (filter pattern: `""` = all logs)

## Verification

### 1. Check subscription filter

```bash
aws logs describe-subscription-filters \
  --log-group-name /aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE
```

### 2. Generate logs

```bash
cd ..
./health.sh
```

### 3. Check S3 bucket (wait ~60 seconds for buffering)

```bash
aws s3 ls s3://finance_personal_assistant-logs-905418344519-us-west-2/logs/ --recursive
```

### 4. Download and view logs

```bash
# List files
aws s3 ls s3://finance_personal_assistant-logs-905418344519-us-west-2/logs/year=2025/ --recursive

# Download and decompress (files are GZIP-compressed by CloudWatch Logs)
aws s3 cp s3://finance-personal-assistant-logs-905418344519-us-west-2/logs/year=2025/month=11/day=21/finance_personal_assistant-logs-1-... - | gunzip | jq
```

## Log Format

Logs are stored as GZIP-compressed JSON:

```json
{
  "messageType": "DATA_MESSAGE",
  "owner": "905418344519",
  "logGroup": "/aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE",
  "logStream": "2025/11/21/[$LATEST]abcdef",
  "subscriptionFilters": ["finance_personal_assistant-to-firehose"],
  "logEvents": [
    {
      "id": "37891234567890123456789012345678901234567890123456789012",
      "timestamp": 1732185600000,
      "message": "[INFO] Agent invoked with payload: {...}"
    }
  ]
}
```

## Configuration

**Buffering**: Firehose writes to S3 when either condition is met:
- 5 MB of data buffered
- 60 seconds elapsed

**Compression**: UNCOMPRESSED in Firehose (CloudWatch Logs subscription filters send GZIP-compressed data, so Firehose stores it as-is to avoid double compression)

**Partitioning**: Date-based for easy querying
```
logs/
  year=2025/
    month=11/
      day=21/
        finance_personal_assistant-logs-1-2025-11-21-...(no .gz extension)
        finance_personal_assistant-logs-2-2025-11-21-...
```

**Error handling**: Failed deliveries go to:
```
errors/
  year=2025/
    month=11/
      day=21/
        !{firehose:error-output-type}/
```

## Cost Estimate

Assuming 1 GB/day of logs:

- **Firehose ingestion**: ~$0.87/month ($0.029/GB × 30 days)
- **S3 storage**: ~$0.69/month ($0.023/GB × 30 GB)
- **Total**: ~$1.56/month

CloudWatch Logs retention costs depend on your configuration.

## Cleanup

```bash
python3 cleanup_firehose.py
```

This removes:
- ✅ Subscription filter
- ✅ Firehose delivery stream
- ✅ IAM roles
- ✅ S3 bucket **and all logs**

**Note**: CloudWatch log group is NOT deleted (managed by AgentCore Runtime).

## Troubleshooting

### No logs appearing in S3

**Possible causes**:

1. **Buffering delay**: Wait at least 60 seconds after generating logs
2. **No logs generated**: Check CloudWatch Logs directly:
   ```bash
   aws logs tail /aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE
   ```
3. **Subscription filter issue**: Verify it exists:
   ```bash
   aws logs describe-subscription-filters \
     --log-group-name /aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE
   ```
4. **Firehose errors**: Check Firehose CloudWatch Logs:
   ```bash
   aws logs tail /aws/kinesisfirehose/finance_personal_assistant-logs --follow
   ```

### Permission errors

Check IAM role trust policies:
```bash
# Firehose role
aws iam get-role --role-name finance_personal_assistant-firehose-role

# Subscription role
aws iam get-role --role-name finance_personal_assistant-logs-to-firehose-role
```

### "Log group does not exist" error

The agent must be deployed first to create the log group:
```bash
cd ..
./launch.sh
```

## References

- [CloudWatch Logs Subscription Filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html)
- [Send CloudWatch Logs to Firehose](https://docs.aws.amazon.com/firehose/latest/dev/writing-with-cloudwatch-logs.html)
- [Firehose Data Delivery](https://docs.aws.amazon.com/firehose/latest/dev/basic-deliver.html)
