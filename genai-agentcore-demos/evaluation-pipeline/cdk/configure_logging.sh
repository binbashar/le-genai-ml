#!/bin/bash
#
# Configure Bedrock Model Invocation Logging
#
# Reads CloudFormation outputs and enables Bedrock logging automatically.
#
set -e

STACK_NAME="EvaluationPipeline"

echo "🔍 Reading stack outputs..."

LOG_GROUP=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`LogGroupName`].OutputValue' \
  --output text)

ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockLoggingRoleArn`].OutputValue' \
  --output text)

if [ -z "$LOG_GROUP" ] || [ -z "$ROLE_ARN" ]; then
    echo "❌ Error: Could not retrieve stack outputs"
    exit 1
fi

echo "📋 Log Group: $LOG_GROUP"
echo "🔐 Role ARN: $ROLE_ARN"
echo ""
echo "⚙️  Configuring Bedrock logging..."

aws bedrock put-model-invocation-logging-configuration \
  --logging-config "{\"cloudWatchConfig\": {\"logGroupName\": \"$LOG_GROUP\", \"roleArn\": \"$ROLE_ARN\"}}"

echo ""
echo "✅ Bedrock model invocation logging enabled!"
echo "   All Bedrock invocations will now be logged to CloudWatch and streamed to S3."
