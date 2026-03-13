# Lambda Transformation Function for Bedrock Model Evaluation

This directory contains a Lambda transformation function that converts AgentCore CloudWatch logs into the JSONL format required for Amazon Bedrock Model Evaluation with LLM-as-a-judge.

## Architecture

```
CloudWatch Logs → Subscription Filter → Firehose → Lambda Transform → S3 (JSONL)
```

1. **CloudWatch Logs**: AgentCore Runtime logs in OpenTelemetry JSON format
2. **Subscription Filter**: Streams logs from CloudWatch to Firehose
3. **Firehose Delivery Stream**: Batches and buffers logs
4. **Lambda Transformation**: Converts logs to Bedrock evaluation format
5. **S3 Destination**: Stores transformed JSONL files ready for evaluation jobs

## Bedrock Evaluation Format

The Lambda function transforms logs into the following JSONL format:

```jsonl
{"prompt":"User's query","modelResponses":[{"response":"Agent's response","modelIdentifier":"agent-name"}]}
{"prompt":"Next query","modelResponses":[{"response":"Next response","modelIdentifier":"agent-name"}]}
```

Each line is a complete JSON object containing:

- **`prompt`** (required): The user's query/input to the agent
- **`modelResponses`** (required): Array with single model response object
  - **`response`**: The agent's complete response
  - **`modelIdentifier`**: Agent name for tracking (e.g., `finance_personal_assistant.DEFAULT`)
- **`category`** (optional): Classification category (not currently used)
- **`referenceResponse`** (optional): Ground truth for correctness evaluation (not currently used)

## Lambda Function Logic

### Input Processing

The Lambda function receives Firehose records containing GZIP-compressed, base64-encoded CloudWatch Logs subscription filter data:

```python
# Decode → Decompress → Parse JSON
compressed_data = base64.b64decode(record["data"])
decompressed_data = gzip.decompress(compressed_data)
log_data = json.loads(decompressed_data)
```

### Conversation Extraction

The function extracts conversation data from OpenTelemetry log events:

```python
def extract_conversation_data(log_entry):
    """
    Looks for:
    - Structured JSON in log body with "prompt"/"response" keys
    - Gen AI attributes (gen_ai.prompt, gen_ai.completion)
    - Trace IDs for grouping prompts with responses
    """
```

**Log patterns recognized:**

1. **Structured JSON in body**:
   ```json
   {
     "body": "{\"prompt\": \"...\", \"response\": \"...\"}",
     "traceId": "trace123"
   }
   ```

2. **Gen AI attributes**:
   ```json
   {
     "attributes": {
       "gen_ai.prompt": "...",
       "gen_ai.completion": "..."
     }
   }
   ```

3. **Text patterns**:
   ```
   "USER PROMPT: How do I create a budget?"
   ```

### Trace Grouping

Prompts and responses are matched using OpenTelemetry trace IDs:

```python
def group_by_trace(conversations):
    """
    Groups conversation fragments by trace ID
    Returns only complete conversations (both prompt and response present)
    """
```

This ensures:
- Each prompt is paired with its corresponding response
- Incomplete conversations (prompt without response) are filtered out
- Multiple conversations in a single log batch are handled correctly

### Output Formatting

The function outputs JSONL format (newline-delimited JSON):

```python
# Each conversation becomes one JSON line
jsonl_lines = []
for conv in complete_conversations:
    bedrock_format = to_bedrock_evaluation_format(conv)
    jsonl_lines.append(json.dumps(bedrock_format))

output_data = "\n".join(jsonl_lines) + "\n"
```

**Result codes:**
- `Ok`: Successfully transformed, data contains JSONL
- `Dropped`: No conversation data found in record
- `ProcessingFailed`: Error during transformation

## Setup and Deployment

### Prerequisites

- Agent deployed with `./launch.sh`
- AWS CLI configured with appropriate permissions
- Python 3.13+ installed locally (for testing)

### Deploy Firehose Pipeline

```bash
cd /path/to/firehose-logging
./setup.sh
```

This script creates:
1. S3 bucket: `{agent-name}-logs-{account}-{region}`
2. Lambda function: `{agent-name}-log-transformer` (Python 3.13 runtime)
3. IAM roles:
   - Lambda execution role with CloudWatch Logs permissions
   - Firehose role with S3 and Lambda invoke permissions
   - CloudWatch Logs role with Firehose put permissions
4. Firehose delivery stream with Lambda processor
5. CloudWatch Logs subscription filter

**Resource naming:**
- Lambda function: `finance_personal_assistant-log-transformer`
- Lambda role: `finance_personal_assistant-lambda-role`
- Firehose role: `finance_personal_assistant-firehose-role`
- Subscription role: `finance_personal_assistant-logs-to-firehose-role`

### Verify Deployment

```bash
# 1. Check Lambda function exists
aws lambda get-function --function-name finance_personal_assistant-log-transformer

# 2. Check Firehose stream
aws firehose describe-delivery-stream --delivery-stream-name finance_personal_assistant-logs

# 3. Check subscription filter
aws logs describe-subscription-filters \
  --log-group-name /aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE-DEFAULT
```

## Testing

### Local Testing

Test the Lambda transformation logic locally:

```bash
cd /path/to/firehose-logging
uv run python test_lambda_transform.py
```

This runs the transformation function with sample data and validates:
- Input/output format correctness
- Trace-based conversation grouping
- JSONL structure for Bedrock evaluation

**Expected output:**
```
✅ Test event created with 1 record(s)
✅ Handler returned successfully
✅ Format validation passed
✅ Transformed 2 conversation(s) to Bedrock evaluation format
```

### End-to-End Testing

1. **Generate agent logs**:
   ```bash
   cd /path/to/finance-personal-assistant/production
   ./health.sh
   ```

2. **Monitor Lambda execution** (wait ~60 seconds for buffering):
   ```bash
   aws logs tail /aws/lambda/finance_personal_assistant-log-transformer --follow
   ```

3. **Check S3 output** (wait ~60-120 seconds):
   ```bash
   aws s3 ls s3://finance-personal-assistant-logs-{account}-{region}/evaluation-data/ --recursive
   ```

4. **View transformed data**:
   ```bash
   # List files
   aws s3 ls s3://finance-personal-assistant-logs-{account}-{region}/evaluation-data/year=2025/month=11/day=21/

   # Download and view
   aws s3 cp s3://finance-personal-assistant-logs-{account}-{region}/evaluation-data/year=2025/month=11/day=21/{filename} - | head -20
   ```

**Expected JSONL output:**
```jsonl
{"prompt":"I make $6000/month and want to save $1000. Help me create a budget.","modelResponses":[{"response":"Here's a budget plan...","modelIdentifier":"finance_personal_assistant.DEFAULT"}]}
{"prompt":"Analyze Apple stock (AAPL) and tell me if it's a good investment.","modelResponses":[{"response":"Apple Inc. (AAPL) Analysis...","modelIdentifier":"finance_personal_assistant.DEFAULT"}]}
```

## Monitoring

### Lambda Logs

Monitor transformation function execution:

```bash
# Real-time logs
aws logs tail /aws/lambda/finance_personal_assistant-log-transformer --follow

# Recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/finance_personal_assistant-log-transformer \
  --filter-pattern "ERROR"
```

**Log messages to look for:**
- `Processing {N} log events in record {recordId}` - Input batch size
- `Extracted {N} conversation fragments` - Conversation detection
- `Found {N} complete conversations` - Successful trace grouping
- `Successfully transformed {N} conversations` - Output success
- `No conversation data found in record {recordId}, dropping` - Empty batch

### Firehose Metrics

Monitor delivery stream performance:

```bash
# Via CloudWatch Metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Firehose \
  --metric-name IncomingRecords \
  --dimensions Name=DeliveryStreamName,Value=finance_personal_assistant-logs \
  --start-time 2025-11-21T00:00:00Z \
  --end-time 2025-11-21T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

**Key metrics:**
- `IncomingRecords`: Records received from CloudWatch Logs
- `DeliveryToS3.Success`: Records successfully written to S3
- `ExecuteProcessing.Success`: Lambda transformation successes
- `ExecuteProcessing.Duration`: Lambda execution time

### Error Handling

**Errors are written to S3 error prefix:**
```
s3://finance-personal-assistant-logs-{account}-{region}/errors/year=2025/...
```

**Common errors:**
- `ProcessingFailed`: Lambda timeout or exception
- `Lambda.ResourceNotFoundException`: Lambda function deleted
- `S3.AccessDenied`: IAM permissions issue

**Troubleshooting:**
1. Check Lambda logs for detailed error messages
2. Verify IAM roles have correct permissions
3. Test Lambda function with `test_lambda_transform.py`
4. Check S3 error prefix for failed records

## Cleanup

Remove all Firehose logging resources:

```bash
cd /path/to/firehose-logging
./cleanup.sh
```

This deletes:
- Subscription filter
- Firehose delivery stream
- Lambda function
- All IAM roles (Lambda, Firehose, CloudWatch Logs)
- S3 bucket and all data

**Note:** CloudWatch log group is NOT deleted (managed by AgentCore Runtime).

## Customization

### Add Ground Truth Responses

To include reference responses for correctness evaluation:

1. **Store ground truth in agent memory or database**
2. **Modify Lambda function** (`lambda_transform.py`):
   ```python
   def to_bedrock_evaluation_format(conversation):
       # Fetch ground truth from external source
       ground_truth = fetch_ground_truth(conversation["prompt"])

       return {
           "prompt": conversation["prompt"],
           "modelResponses": [...],
           "referenceResponse": ground_truth,  # Add this
       }
   ```

3. **Redeploy Lambda**:
   ```bash
   ./setup.sh  # Updates existing Lambda function code
   ```

### Add Category Classification

To categorize prompts (e.g., "Budget", "Investment", "Spending"):

```python
def classify_prompt(prompt):
    """Simple keyword-based classification"""
    prompt_lower = prompt.lower()
    if any(word in prompt_lower for word in ["budget", "allocate", "distribute"]):
        return "Budget"
    elif any(word in prompt_lower for word in ["stock", "invest", "portfolio"]):
        return "Investment"
    elif any(word in prompt_lower for word in ["spend", "purchase", "expense"]):
        return "Spending"
    return "General"

def to_bedrock_evaluation_format(conversation):
    return {
        "prompt": conversation["prompt"],
        "modelResponses": [...],
        "category": classify_prompt(conversation["prompt"]),  # Add this
    }
```

### Adjust Buffering

Modify buffering settings in `setup_firehose.py`:

```python
# S3 buffering (how often to write files)
"BufferingHints": {
    "SizeInMBs": 5,           # Write when 5MB accumulated
    "IntervalInSeconds": 60,  # Or every 60 seconds
}

# Lambda buffering (how often to invoke Lambda)
"Parameters": [
    {
        "ParameterName": "BufferSizeInMBs",
        "ParameterValue": "3",  # Invoke Lambda with 3MB batches
    },
    {
        "ParameterName": "BufferIntervalInSeconds",
        "ParameterValue": "60",  # Or every 60 seconds
    },
]
```

**Trade-offs:**
- Smaller buffers → More frequent Lambda invocations → Higher cost
- Larger buffers → Fewer invocations → Lower cost, higher latency

## Using Data for Bedrock Evaluation

Once data is in S3, use it for model evaluation jobs:

### Via AWS Console

1. Go to Amazon Bedrock → Model Evaluation
2. Click "Create evaluation job"
3. Choose "LLM as a judge"
4. Select evaluation metrics (Correctness, Relevance, Harmfulness, etc.)
5. Specify S3 input dataset location:
   ```
   s3://finance-personal-assistant-logs-{account}-{region}/evaluation-data/
   ```
6. Choose evaluator model (e.g., Claude 3.5 Sonnet)
7. Run evaluation job

### Via AWS CLI

```bash
aws bedrock create-model-evaluation-job \
  --job-name "finance-assistant-eval-$(date +%Y%m%d)" \
  --evaluation-config '{
    "automated": {
      "datasetMetricConfigs": [{
        "taskType": "LLM_AS_JUDGE",
        "dataset": {
          "name": "finance-assistant-logs",
          "datasetLocation": {
            "s3Uri": "s3://finance-personal-assistant-logs-{account}-{region}/evaluation-data/"
          }
        },
        "metricNames": ["Builtin.Correctness", "Builtin.Relevance", "Builtin.Harmfulness"]
      }]
    }
  }' \
  --inference-config '{
    "models": [{
      "bedrockModel": {
        "modelIdentifier": "anthropic.claude-3-5-sonnet-20241022-v2:0"
      }
    }]
  }' \
  --role-arn "arn:aws:iam::{account}:role/BedrockEvaluationRole" \
  --output-data-config '{
    "s3Uri": "s3://finance-personal-assistant-logs-{account}-{region}/evaluation-results/"
  }'
```

### Evaluation Metrics

**Built-in metrics for LLM-as-a-judge:**

- **Correctness** (`Builtin.Correctness`): Factual accuracy of responses
- **Relevance** (`Builtin.Relevance`): How well response addresses the prompt
- **Harmfulness** (`Builtin.Harmfulness`): Detects harmful, biased, or toxic content
- **Completeness** (`Builtin.Completeness`): Coverage of all aspects in prompt
- **Coherence** (`Builtin.Coherence`): Logical flow and structure

**Custom metrics:**
- Define custom rubrics in JSON format
- Use your own evaluation criteria

## References

- [AWS Bedrock Model Evaluation Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-judge-create.html)
- [Prompt Dataset Format](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-prompt-datasets-judge.html)
- [LLM-as-a-Judge Blog Post](https://aws.amazon.com/blogs/machine-learning/llm-as-a-judge-on-amazon-bedrock-model-evaluation/)
- [Firehose Data Transformation](https://docs.aws.amazon.com/firehose/latest/dev/data-transformation.html)

## Troubleshooting

### No data in S3 after 2 minutes

1. Check subscription filter exists:
   ```bash
   aws logs describe-subscription-filters --log-group-name /aws/bedrock-agentcore/runtimes/...
   ```

2. Verify agent logs are being generated:
   ```bash
   aws logs tail /aws/bedrock-agentcore/runtimes/... --follow
   ```

3. Check Firehose stream status:
   ```bash
   aws firehose describe-delivery-stream --delivery-stream-name finance_personal_assistant-logs
   ```

### Lambda transformation errors

1. Check Lambda logs:
   ```bash
   aws logs tail /aws/lambda/finance_personal_assistant-log-transformer --follow
   ```

2. Test locally:
   ```bash
   uv run python test_lambda_transform.py
   ```

3. Verify Lambda has correct IAM permissions

### Invalid JSONL format

1. Download sample file from S3
2. Validate each line is valid JSON:
   ```bash
   cat sample.jsonl | while read line; do echo "$line" | jq .; done
   ```

3. Check Lambda transformation logic matches Bedrock format requirements

### High Lambda costs

- Increase buffer sizes to reduce invocation frequency
- Filter logs at subscription filter level to reduce volume
- Optimize Lambda memory allocation (currently 512MB)
