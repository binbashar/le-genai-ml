#!/bin/bash
# Downloads latest Parquet and displays prompt/response for PII demo

BUCKET="eval-pipeline-905418344519-us-west-2"
AGENT="finance_personal_assistant"

echo "Fetching latest Parquet file..."

# Get latest file
LATEST=$(aws s3 ls "s3://${BUCKET}/staging/agent_name=${AGENT}/" --recursive --profile binbash | sort | tail -1 | awk '{print $4}')

if [ -z "$LATEST" ]; then
    echo "No Parquet files found for agent: ${AGENT}"
    exit 1
fi

echo "Downloading: ${LATEST}"
aws s3 cp "s3://${BUCKET}/${LATEST}" /tmp/latest.parquet --profile binbash --quiet

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
