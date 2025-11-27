#!/bin/bash
#
# Sync Firehose output bucket to local folder for exploration
#
# Usage:
#   ./sync_output.sh [local_folder]
#
# Examples:
#   ./sync_output.sh                    # Syncs to ./evaluation-data-local/
#   ./sync_output.sh ~/my-eval-data     # Syncs to custom folder
#

set -e

# Load agent configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="$SCRIPT_DIR/../.bedrock_agentcore.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Agent config not found at $CONFIG_FILE"
    echo "   Please deploy the agent first using: cd .. && ./launch.sh"
    exit 1
fi

# Extract agent name, account, region from .bedrock_agentcore.yaml
AGENT_NAME=$(grep "default_agent:" "$CONFIG_FILE" | awk '{print $2}' | tr -d '"' | tr -d "'")
REGION=$(grep "region:" "$CONFIG_FILE" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
ACCOUNT=$(grep "account:" "$CONFIG_FILE" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")

if [ -z "$AGENT_NAME" ] || [ -z "$REGION" ] || [ -z "$ACCOUNT" ]; then
    echo "❌ Failed to parse agent configuration from $CONFIG_FILE"
    exit 1
fi

# S3 bucket name (replace underscores with hyphens)
AGENT_NAME_SAFE=$(echo "$AGENT_NAME" | tr '_' '-')
BUCKET_NAME="${AGENT_NAME_SAFE}-logs-${ACCOUNT}-${REGION}"

# Local folder (default or provided)
LOCAL_FOLDER="${1:-./evaluation-data-local}"

echo "="
echo "Sync Firehose Output to Local Folder"
echo "="
echo
echo "📋 Configuration:"
echo "   Agent Name: $AGENT_NAME"
echo "   Region: $REGION"
echo "   Account: $ACCOUNT"
echo "   S3 Bucket: s3://$BUCKET_NAME/evaluation-data/"
echo "   Local Folder: $LOCAL_FOLDER"
echo

# Check if bucket exists
if ! AWS_PROFILE=binbash aws s3 ls "s3://$BUCKET_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "❌ Bucket does not exist: s3://$BUCKET_NAME"
    echo "   Have you set up Firehose logging? Run: ./setup.sh"
    exit 1
fi

# Check if evaluation-data prefix has any objects
OBJECT_COUNT=$(AWS_PROFILE=binbash aws s3 ls "s3://$BUCKET_NAME/evaluation-data/" --recursive --region "$REGION" | wc -l)

if [ "$OBJECT_COUNT" -eq 0 ]; then
    echo "⚠️  No data found in s3://$BUCKET_NAME/evaluation-data/"
    echo "   This may be because:"
    echo "   1. No agent invocations have occurred yet (run: cd .. && ./health.sh)"
    echo "   2. Firehose buffering delay (~60 seconds)"
    echo "   3. Lambda transformation errors (check logs: aws logs tail /aws/lambda/${AGENT_NAME}-log-transformer --follow)"
    echo
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Create local folder
mkdir -p "$LOCAL_FOLDER"

# Sync S3 bucket to local folder
echo "🔄 Syncing s3://$BUCKET_NAME/evaluation-data/ to $LOCAL_FOLDER ..."
echo

AWS_PROFILE=binbash aws s3 sync \
    "s3://$BUCKET_NAME/evaluation-data/" \
    "$LOCAL_FOLDER" \
    --region "$REGION" \
    --no-progress

echo
echo "="
echo "✅ Sync Complete!"
echo "="
echo
echo "📂 Local Data:"
echo "   Folder: $LOCAL_FOLDER"
echo "   Files:"
find "$LOCAL_FOLDER" -type f -name "*.json" -o -name "*.jsonl" | head -10

FILE_COUNT=$(find "$LOCAL_FOLDER" -type f | wc -l | tr -d ' ')
if [ "$FILE_COUNT" -gt 10 ]; then
    echo "   ... and $(($FILE_COUNT - 10)) more files"
fi

echo
echo "🔍 Explore Data:"
echo "   # View first file"
echo "   cat \$(find $LOCAL_FOLDER -type f -name '*.json*' | head -1)"
echo
echo "   # Count total records (JSONL format)"
echo "   find $LOCAL_FOLDER -type f -name '*.json*' -exec cat {} \; | wc -l"
echo
echo "   # View sample record with jq"
echo "   find $LOCAL_FOLDER -type f -name '*.json*' -exec cat {} \; | head -1 | jq ."
echo
echo "📊 Next Steps:"
echo "   - Explore data in: $LOCAL_FOLDER"
echo "   - Use data for Bedrock Model Evaluation"
echo "   - Create custom evaluation datasets (filter, transform, etc.)"
echo
