#!/bin/bash
set -e

echo "=== Phase 1 Test: Data Flow Validation ==="
echo ""

# ============================================================================
# Configuration
# ============================================================================

AGENT_ARN="${AGENT_ARN:-arn:aws:bedrock-agentcore:us-west-2:905418344519:runtime/finance_personal_assistant}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-905418344519}"
REGION="${AWS_REGION:-us-west-2}"
BUCKET="genai-agentcore-demos-evaluation-pipeline-${ACCOUNT_ID}-${REGION}"
SESSION_ID="test-$(uuidgen | tr '[:upper:]' '[:lower:]')"
LOG_GROUP="bedrock-model-invocations-eval"

echo "Configuration:"
echo "  Agent ARN: $AGENT_ARN"
echo "  Bucket: $BUCKET"
echo "  Session ID: $SESSION_ID"
echo "  Log Group: $LOG_GROUP"
echo ""

# ============================================================================
# Step 1: Invoke Agent with Test Prompt
# ============================================================================

echo "Step 1: Invoking agent with test prompt..."
TIMESTAMP=$(date -Iseconds)
TEST_PROMPT="Test invocation for evaluation pipeline at $TIMESTAMP. This is a data flow validation."

aws bedrock-agentcore invoke-agent-runtime \
  --agent-identifier "$AGENT_ARN" \
  --session-id "$SESSION_ID" \
  --input "{\"prompt\": \"$TEST_PROMPT\"}" \
  --profile binbash \
  > /tmp/agent_response.json 2>&1

if [ $? -eq 0 ]; then
  echo "   ✅ Agent invoked successfully"
  echo "   Response preview: $(cat /tmp/agent_response.json | jq -r '.completion // .output // "Response received"' 2>/dev/null | head -c 100)..."
else
  echo "   ❌ FAIL: Agent invocation failed"
  cat /tmp/agent_response.json
  exit 1
fi
echo ""

# ============================================================================
# Step 2: Verify CloudWatch Logs (Optional - Fast Check)
# ============================================================================

echo "Step 2: Checking CloudWatch Logs for invocation..."
sleep 5  # Wait for logs to appear

RECENT_LOGS=$(aws logs tail "$LOG_GROUP" \
  --since 30s \
  --format short \
  --profile binbash \
  2>/dev/null | grep -i "modelId" | head -1)

if [ -n "$RECENT_LOGS" ]; then
  echo "   ✅ Bedrock invocation logged to CloudWatch"
  echo "   Sample: $(echo "$RECENT_LOGS" | cut -c1-100)..."
else
  echo "   ⚠️  WARNING: No logs found yet (may need more time)"
fi
echo ""

# ============================================================================
# Step 3: Wait for Firehose Buffer to Flush
# ============================================================================

echo "Step 3: Waiting 90 seconds for Firehose buffer to flush..."
echo "   (Firehose buffer: 60s or 1MB, whichever comes first)"
for i in {1..9}; do
  sleep 10
  echo "   ... ${i}0 seconds elapsed"
done
echo "   ✅ Wait complete"
echo ""

# ============================================================================
# Step 4: Check S3 for New Files
# ============================================================================

echo "Step 4: Checking S3 for new files in raw/ prefix..."

# List recent files (last 5)
LATEST_FILES=$(aws s3 ls "s3://$BUCKET/raw/" \
  --recursive \
  --human-readable \
  --profile binbash \
  2>/dev/null | tail -5)

if [ -z "$LATEST_FILES" ]; then
  echo "   ❌ FAIL: No files found in S3 raw/ prefix"
  echo ""
  echo "Diagnostic checks:"
  echo "1. Verify Firehose stream exists:"
  aws firehose describe-delivery-stream \
    --delivery-stream-name evaluation-pipeline-cloudwatch-to-s3 \
    --profile binbash \
    --query 'DeliveryStreamDescription.DeliveryStreamStatus' 2>/dev/null || echo "   ❌ Firehose stream not found"

  echo ""
  echo "2. Check CloudWatch Logs subscription filters:"
  aws logs describe-subscription-filters \
    --log-group-name "$LOG_GROUP" \
    --profile binbash \
    2>/dev/null || echo "   ❌ No subscription filters found"

  echo ""
  echo "3. Check Firehose errors:"
  aws logs tail /aws/kinesisfirehose/evaluation-pipeline \
    --since 5m \
    --format short \
    --profile binbash \
    2>/dev/null | grep -i error | head -5 || echo "   No errors in Firehose logs"

  exit 1
fi

echo "   ✅ Files found in S3:"
echo "$LATEST_FILES"
echo ""

# ============================================================================
# Step 5: Download and Inspect Latest File
# ============================================================================

echo "Step 5: Downloading latest file for inspection..."

# Extract the most recent file path
LATEST_FILE=$(echo "$LATEST_FILES" | tail -1 | awk '{print $NF}')
echo "   Latest file: $LATEST_FILE"

aws s3 cp "s3://$BUCKET/$LATEST_FILE" /tmp/test_raw.json.gz --profile binbash 2>&1

if [ $? -ne 0 ]; then
  echo "   ❌ FAIL: Could not download file"
  exit 1
fi

echo "   ✅ File downloaded: $(ls -lh /tmp/test_raw.json.gz | awk '{print $5}')"
echo ""

# ============================================================================
# Step 6: Decompress and Validate Structure
# ============================================================================

echo "Step 6: Decompressing and inspecting file structure..."

# Decompress
gunzip -c /tmp/test_raw.json.gz > /tmp/test_raw.json 2>&1

if [ $? -ne 0 ]; then
  echo "   ❌ FAIL: File is not valid GZIP"
  file /tmp/test_raw.json.gz
  exit 1
fi

echo "   ✅ File decompressed successfully"
echo ""

# Display first 20 lines
echo "   File preview (first 20 lines):"
head -20 /tmp/test_raw.json | sed 's/^/     /'
echo ""

# ============================================================================
# Step 7: Validate Bedrock Log Structure
# ============================================================================

echo "Step 7: Validating Bedrock invocation log structure..."

# Check for required fields in CloudWatch Logs format
HAS_LOG_EVENTS=$(jq -e '.logEvents' /tmp/test_raw.json >/dev/null 2>&1 && echo "yes" || echo "no")
HAS_MESSAGE=$(jq -e '.logEvents[0].message' /tmp/test_raw.json >/dev/null 2>&1 && echo "yes" || echo "no")

if [ "$HAS_LOG_EVENTS" != "yes" ]; then
  echo "   ❌ FAIL: File does not contain 'logEvents' array (not CloudWatch Logs format)"
  jq '.' /tmp/test_raw.json | head -20
  exit 1
fi

echo "   ✅ CloudWatch Logs format detected"

if [ "$HAS_MESSAGE" != "yes" ]; then
  echo "   ❌ FAIL: No message field in log events"
  jq '.logEvents[0]' /tmp/test_raw.json
  exit 1
fi

# Parse the message field as JSON and check for Bedrock invocation structure
MESSAGE_JSON=$(jq -r '.logEvents[0].message' /tmp/test_raw.json)
HAS_MODEL_ID=$(echo "$MESSAGE_JSON" | jq -e '.modelId' >/dev/null 2>&1 && echo "yes" || echo "no")
HAS_INPUT=$(echo "$MESSAGE_JSON" | jq -e '.input' >/dev/null 2>&1 && echo "yes" || echo "no")
HAS_OUTPUT=$(echo "$MESSAGE_JSON" | jq -e '.output' >/dev/null 2>&1 && echo "yes" || echo "no")
HAS_TIMESTAMP=$(echo "$MESSAGE_JSON" | jq -e '.timestamp' >/dev/null 2>&1 && echo "yes" || echo "no")

if [ "$HAS_MODEL_ID" = "yes" ] && [ "$HAS_INPUT" = "yes" ] && [ "$HAS_OUTPUT" = "yes" ] && [ "$HAS_TIMESTAMP" = "yes" ]; then
  echo "   ✅ Bedrock invocation log structure valid"
  echo ""
  echo "   Key fields found:"
  echo "     - modelId: $(echo "$MESSAGE_JSON" | jq -r '.modelId')"
  echo "     - operation: $(echo "$MESSAGE_JSON" | jq -r '.operation // "N/A"')"
  echo "     - timestamp: $(echo "$MESSAGE_JSON" | jq -r '.timestamp')"
  echo "     - input tokens: $(echo "$MESSAGE_JSON" | jq -r '.input.inputTokenCount // "N/A"')"
  echo "     - output tokens: $(echo "$MESSAGE_JSON" | jq -r '.output.outputTokenCount // "N/A"')"
else
  echo "   ❌ FAIL: Message does not contain expected Bedrock invocation structure"
  echo "   Expected fields: modelId, input, output, timestamp"
  echo "   Found:"
  echo "     - modelId: $HAS_MODEL_ID"
  echo "     - input: $HAS_INPUT"
  echo "     - output: $HAS_OUTPUT"
  echo "     - timestamp: $HAS_TIMESTAMP"
  echo ""
  echo "   Message content:"
  echo "$MESSAGE_JSON" | jq '.' | head -20
  exit 1
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "================================================================="
echo "=== Phase 1 Test: SUCCESS ==="
echo "================================================================="
echo ""
echo "✅ CloudWatch → Firehose → S3 pipeline operational"
echo "✅ Data contains complete Bedrock invocation logs"
echo "✅ File format: GZIP-compressed JSON (CloudWatch Logs format)"
echo "✅ All required fields present (modelId, input, output, timestamp)"
echo ""
echo "Next steps:"
echo "  1. ✅ Phase 1 validated - ready for Phase 2"
echo "  2. Phase 2: Implement Lambda transformer (CloudWatch JSON → Parquet)"
echo "  3. Phase 2: Add PII scrubbing to Lambda"
echo "  4. Phase 2: Enable Firehose data transformation"
echo ""
echo "Test artifacts:"
echo "  - Session ID: $SESSION_ID"
echo "  - S3 file: s3://$BUCKET/$LATEST_FILE"
echo "  - Local file: /tmp/test_raw.json"
echo ""

exit 0
