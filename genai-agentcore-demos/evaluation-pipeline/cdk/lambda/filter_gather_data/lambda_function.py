"""
Filter and Gather Data Lambda - Step Functions Task

Reads Parquet files from S3 staging, applies filters, performs sampling,
and generates JSONL dataset in Bedrock evaluation format.

Input (from Step Functions):
{
  "agent_name": "finance-personal-assistant",
  "start_date": "2025-11-24T00:00:00Z",   # ISO 8601 UTC (recommended)
  "end_date": "2025-11-24T23:59:59Z",     # ISO 8601 UTC (recommended)
  "limit": 100,
  "metrics": ["Builtin.Correctness"]
}

Date formats accepted:
- ISO 8601 with time: "2025-11-24T00:00:00Z" (recommended)
- Date only: "2025-11-24" (normalized to 00:00:00Z for start, 23:59:59Z for end)

Output:
{
  "dataset_s3_uri": "s3://bucket/evaluation-datasets/{agent}/{timestamp}/dataset.jsonl",
  "question_count": 95,
  "sampling_stats": {
    "total_records": 1000,
    "filtered_records": 800,
    "sampled_records": 95
  }
}
"""

import boto3
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from io import BytesIO

import pyarrow.parquet as pq

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')


def normalize_date(date_str: str, is_end_date: bool = False) -> str:
    """
    Normalize date string to ISO 8601 UTC format.

    Accepts:
    - YYYY-MM-DD (date only) -> adds T00:00:00Z or T23:59:59Z
    - YYYY-MM-DDTHH:MM:SSZ (full ISO 8601)

    Args:
        date_str: Date string in either format
        is_end_date: If True and date-only input, use 23:59:59Z instead of 00:00:00Z

    Returns:
        ISO 8601 UTC format: YYYY-MM-DDTHH:MM:SSZ
    """
    if 'T' in date_str:
        return date_str  # Already has time component
    # Date-only: add default time (full day range)
    time_suffix = "T23:59:59Z" if is_end_date else "T00:00:00Z"
    return date_str + time_suffix


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for filtering and gathering evaluation data.

    Args:
        event: Configuration from Step Functions
        context: Lambda context

    Returns:
        Dataset metadata and S3 location
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Extract configuration
    config = event
    agent_name = config['agent_name']
    start_date = normalize_date(config['start_date'], is_end_date=False)
    end_date = normalize_date(config['end_date'], is_end_date=True)
    limit = config['limit']

    logger.info(f"Normalized dates: start={start_date}, end={end_date}")

    # Get S3 bucket from environment
    bucket_name = os.environ.get('STAGING_BUCKET')
    if not bucket_name:
        raise ValueError("STAGING_BUCKET environment variable not set")

    # Step 1: List and read Parquet files from staging
    logger.info(f"Reading staging data for agent={agent_name}, date_range={start_date} to {end_date}")
    records = read_staging_data(
        bucket_name=bucket_name,
        agent_name=agent_name,
        start_date=start_date,
        end_date=end_date
    )

    total_records = len(records)
    logger.info(f"Found {total_records} total records in staging")

    # Step 2: Apply sampling (simple random for MVP, can add stratified later)
    sampled_records = apply_sampling(records, limit)
    sampled_count = len(sampled_records)
    logger.info(f"Sampled {sampled_count} records (limit: {limit})")

    # Step 3: Transform to Bedrock evaluation format
    evaluation_dataset = transform_to_bedrock_format(sampled_records, agent_name)

    # Step 4: Write JSONL to S3
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    dataset_key = f"evaluation-datasets/{agent_name}/{timestamp}/dataset.jsonl"
    dataset_s3_uri = write_jsonl_to_s3(
        bucket_name=bucket_name,
        key=dataset_key,
        records=evaluation_dataset
    )

    # Step 5: Write sampling stats
    stats = {
        'total_records': total_records,
        'filtered_records': total_records,  # No filtering yet (MVP)
        'sampled_records': sampled_count,
        'timestamp': timestamp
    }

    stats_key = f"evaluation-datasets/{agent_name}/{timestamp}/sampling_stats.json"
    write_json_to_s3(
        bucket_name=bucket_name,
        key=stats_key,
        data=stats
    )

    # Return results to Step Functions
    return {
        'dataset_s3_uri': dataset_s3_uri,
        'question_count': sampled_count,
        'sampling_stats': stats
    }


def read_staging_data(
    bucket_name: str,
    agent_name: str,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """
    Read Parquet files from S3 staging with date filtering.

    Args:
        bucket_name: S3 bucket name
        agent_name: Agent name for partition filtering
        start_date: Start date (ISO 8601 UTC: YYYY-MM-DDTHH:MM:SSZ)
        end_date: End date (ISO 8601 UTC: YYYY-MM-DDTHH:MM:SSZ)

    Returns:
        List of records from Parquet files
    """
    records = []

    # Parse ISO 8601 dates (replace Z with +00:00 for fromisoformat compatibility)
    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    # Extract date-only for S3 partition queries (partitions are date-based)
    current_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    while current_dt <= end_dt:
        date_str = current_dt.strftime('%Y-%m-%d')
        prefix = f"staging/agent_name={agent_name}/date={date_str}/"

        logger.info(f"Listing objects in prefix: {prefix}")

        try:
            # List all Parquet files for this partition
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                logger.warning(f"No files found in prefix: {prefix}")
                current_dt += timedelta(days=1)
                continue

            # Read each Parquet file
            for obj in response['Contents']:
                key = obj['Key']

                if not key.endswith('.parquet'):
                    continue

                logger.info(f"Reading Parquet file: {key}")

                # Download Parquet file
                parquet_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
                parquet_bytes = parquet_obj['Body'].read()

                # Read with PyArrow
                table = pq.read_table(BytesIO(parquet_bytes))

                # Convert to list of dicts
                df = table.to_pandas()
                file_records = df.to_dict('records')

                records.extend(file_records)
                logger.info(f"Read {len(file_records)} records from {key}")

        except Exception as e:
            logger.error(f"Error reading partition {prefix}: {str(e)}", exc_info=True)

        current_dt += timedelta(days=1)

    return records


def apply_sampling(records: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Apply sampling to limit dataset size (MVP: simple random sampling).

    Future: Add stratified sampling by category.

    Args:
        records: List of records
        limit: Maximum number of records

    Returns:
        Sampled records
    """
    if len(records) <= limit:
        return records

    # Simple random sampling (MVP)
    import random
    random.seed(42)  # Reproducible sampling
    return random.sample(records, limit)


def transform_to_bedrock_format(
    records: List[Dict[str, Any]],
    agent_name: str
) -> List[Dict[str, Any]]:
    """
    Transform staging records to Bedrock evaluation JSONL format.

    Bedrock format:
    {
      "prompt": "What is my budget?",
      "modelResponses": [{
        "response": "Based on your profile...",
        "modelIdentifier": "finance-personal-assistant"
      }],
      "category": "budgeting" (optional)
    }

    Args:
        records: Staging records (from Parquet)
        agent_name: Agent identifier

    Returns:
        List of records in Bedrock format
    """
    evaluation_records = []

    for record in records:
        # Extract prompt and response
        prompt = record.get('prompt', '')
        response = record.get('response', '')

        # Skip records with missing data
        if not prompt or not response:
            logger.warning(f"Skipping record with missing prompt/response: {record.get('request_id')}")
            continue

        # Transform to Bedrock format
        eval_record = {
            'prompt': prompt,
            'modelResponses': [{
                'response': response,
                'modelIdentifier': agent_name
            }]
        }

        # Add optional category if available
        if 'category' in record and record['category']:
            eval_record['category'] = record['category']

        evaluation_records.append(eval_record)

    return evaluation_records


def write_jsonl_to_s3(
    bucket_name: str,
    key: str,
    records: List[Dict[str, Any]]
) -> str:
    """
    Write JSONL (newline-delimited JSON) to S3.

    Args:
        bucket_name: S3 bucket name
        key: S3 key
        records: List of records to write

    Returns:
        S3 URI of written file
    """
    # Convert to JSONL format
    jsonl_lines = [json.dumps(record) for record in records]
    jsonl_content = '\n'.join(jsonl_lines)

    # Upload to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=jsonl_content.encode('utf-8'),
        ContentType='application/x-ndjson',
        ServerSideEncryption='AES256'
    )

    s3_uri = f"s3://{bucket_name}/{key}"
    logger.info(f"Wrote {len(records)} records to {s3_uri}")

    return s3_uri


def write_json_to_s3(
    bucket_name: str,
    key: str,
    data: Dict[str, Any]
) -> str:
    """
    Write JSON to S3.

    Args:
        bucket_name: S3 bucket name
        key: S3 key
        data: Data to write

    Returns:
        S3 URI of written file
    """
    json_content = json.dumps(data, indent=2)

    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json_content.encode('utf-8'),
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )

    s3_uri = f"s3://{bucket_name}/{key}"
    logger.info(f"Wrote JSON to {s3_uri}")

    return s3_uri
