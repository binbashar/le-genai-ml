# Bedrock Invocation Logs Guide

How to analyze Bedrock model invocation logs using `scripts/analyze_bedrock_logs.py`.

## Log Location

```
s3://your-bucket/invocation-logging/AWSLogs/{account}/BedrockModelInvocationLogs/{region}/YYYY/MM/DD/HH/
```

Files are gzip-compressed JSONL.

## Log Structure

See [SCHEMAS.md](../SCHEMAS.md) for complete schema. Key extraction paths:

```python
prompt = input.inputBodyJson.messages[-1].content[].text
response = output.outputBodyJson.output.message.content[].text
tokens = output.outputBodyJson.usage.totalTokens
latency = output.outputBodyJson.metrics.latencyMs
```

## Using the Analyzer Tool

### Search for Prompts

```bash
uv run python scripts/analyze_bedrock_logs.py search "Hello world" \
  --bucket bb-bedrock-invocations-ab4d1c24 \
  --hours 24 \
  --max-results 10
```

### Analyze Conversations

```bash
uv run python scripts/analyze_bedrock_logs.py conversation \
  --bucket bb-bedrock-invocations-ab4d1c24 \
  --hours 6
```

### View Log Structure

```bash
uv run python scripts/analyze_bedrock_logs.py structure \
  --bucket bb-bedrock-invocations-ab4d1c24
```

## CLI Options

```
--bucket BUCKET    S3 bucket name (required)
--profile PROFILE  AWS profile (default: binbash)
--region REGION    AWS region (default: us-west-2)
--hours HOURS      Hours back to search (default: 24)
--max-results N    Max results (default: 10)
```

## Use Cases

| Task | Command |
|------|---------|
| Debug user issue | `search "user's exact prompt"` |
| Monitor quality | `conversation --hours 6` |
| Analyze costs | Parse `usage.totalTokens` from logs |

## Athena Queries (Optional)

For large-scale analysis, create an Athena table over the S3 logs:

```sql
-- Find high-token queries
SELECT timestamp, requestId,
       output.outputBodyJson.usage.totalTokens as tokens
FROM bedrock_logs
WHERE output.outputBodyJson.usage.totalTokens > 5000
ORDER BY tokens DESC LIMIT 10;
```

## References

- [SCHEMAS.md](../SCHEMAS.md) - Complete log schema
- [PRD.md](../PRD.md) - Pipeline architecture
