#!/bin/bash
# Downloads Parquet and displays prompt/response for PII demo
# Usage: ./view_parquet.sh [S3_URI]
# If no S3_URI provided, fetches latest file for default agent

BUCKET="eval-pipeline-905418344519-us-west-2"
AGENT="finance_personal_assistant"

if [ -n "$1" ]; then
    # Use provided S3 URI
    S3_URI="$1"
    echo "Using provided S3 URI: ${S3_URI}"
    aws s3 cp "${S3_URI}" /tmp/latest.parquet --profile binbash --quiet
else
    # Fetch latest file
    echo "Fetching latest Parquet file for agent: ${AGENT}..."
    LATEST=$(aws s3 ls "s3://${BUCKET}/staging/agent_name=${AGENT}/" --recursive --profile binbash | sort | tail -1 | awk '{print $4}')

    if [ -z "$LATEST" ]; then
        echo "No Parquet files found for agent: ${AGENT}"
        exit 1
    fi

    echo "Downloading: ${LATEST}"
    aws s3 cp "s3://${BUCKET}/${LATEST}" /tmp/latest.parquet --profile binbash --quiet
fi

# Display with Python
cd "$(dirname "$0")/cdk" && uv run python3 -c "
import pyarrow.parquet as pq

df = pq.read_table('/tmp/latest.parquet').to_pandas()
row = df.iloc[-1]  # Most recent record

print()
print('=' * 60)
print('PROMPT (filtered):')
print('=' * 60)
print(row['prompt'])
print()
print('=' * 60)
print('RESPONSE (filtered):')
print('=' * 60)
print(row['response'])
print()
"
