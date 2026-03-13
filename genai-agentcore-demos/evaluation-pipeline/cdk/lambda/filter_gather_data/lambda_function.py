"""
Filter and Gather Data Lambda - Step Functions Task

Reads Parquet files from S3 staging, applies filters, performs sampling,
and generates JSONL dataset in Bedrock evaluation format.

Input (from Step Functions):
{
  "agent_name": "finance-personal-assistant",
  "start_date": "2025-11-24T00:00:00Z",   # ISO 8601 UTC
  "end_date": "2025-11-24T23:59:59Z",     # ISO 8601 UTC
  "limit": 100,
  "metrics": ["Builtin.Correctness"],
  "strip_context": true,                   # Optional: Extract user question from full prompt (default: true)
  "include_context_as_reference": false    # Optional: Put context in referenceResponse (default: false)
}

Context Handling:
- strip_context=true (default): Extracts user question from prompts containing:
  - <retrieved_memories>...</retrieved_memories> wrapper
  - [Vision Analysis: ...] prefix
  - [CSV File Data]...User Query: pattern
- include_context_as_reference=true: Puts extracted context in referenceResponse field
  (useful for Correctness/Completeness metrics that can use reference data)

Environment Variables:
- STAGING_BUCKET: S3 bucket name (required)
- STRIP_CONTEXT: Default value for strip_context (default: "true")
- INCLUDE_CONTEXT_AS_REFERENCE: Default value for include_context_as_reference (default: "false")

Date formats accepted (all times in UTC):
- Date only: "2025-11-24" (normalized to 00:00:00Z for start, 23:59:59Z for end)
- With hour:minute: "2025-11-24T14:00Z" (normalized to 14:00:00Z)
- Full ISO 8601: "2025-11-24T14:30:00Z"

S3 Structure (Hive-style partitioning):
staging/agent_name={name}/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/*.parquet

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
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from io import BytesIO

import pyarrow.parquet as pq

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client("s3")


def normalize_date(date_str: str, is_end_date: bool = False) -> str:
    """
    Normalize date string to ISO 8601 UTC format.

    Accepts:
    - YYYY-MM-DD (date only) -> adds T00:00:00Z or T23:59:59Z
    - YYYY-MM-DDTHH:MMZ (hour:minute) -> adds :00 seconds
    - YYYY-MM-DDTHH:MM:SSZ (full ISO 8601) -> unchanged

    Args:
        date_str: Date string in any accepted format
        is_end_date: If True and date-only input, use 23:59:59Z instead of 00:00:00Z

    Returns:
        ISO 8601 UTC format: YYYY-MM-DDTHH:MM:SSZ
    """
    if "T" not in date_str:
        # Date only: YYYY-MM-DD -> add full day range
        time_suffix = "T23:59:59Z" if is_end_date else "T00:00:00Z"
        return date_str + time_suffix

    # Has time component - check if missing seconds
    if date_str.count(":") == 1:
        # Format: YYYY-MM-DDTHH:MMZ -> add :00 before Z
        return date_str.replace("Z", ":00Z")

    return date_str  # Full format: YYYY-MM-DDTHH:MM:SSZ


def extract_user_question(full_prompt: str) -> Tuple[str, str]:
    """
    Extract user question from context-augmented prompt.

    Handles prompt structures with:
    - <retrieved_memories>...</retrieved_memories> wrapper
    - [Vision Analysis: ...] prefix
    - [CSV File Data]...User Query: pattern
    - [Document Error: ...] prefix

    Args:
        full_prompt: Full prompt with memory/vision/csv context

    Returns:
        (user_question, context) tuple
        - user_question: The extracted user question
        - context: The extracted context (empty string if none)
    """
    context_parts = []
    content = full_prompt

    # 1. Handle <retrieved_memories>...</retrieved_memories>\n\nUser: pattern
    if "<retrieved_memories>" in content:
        mem_match = re.search(
            r"<retrieved_memories>(.*?)</retrieved_memories>", content, re.DOTALL
        )
        if mem_match:
            context_parts.append(f"[Retrieved Memories]\n{mem_match.group(1).strip()}")

        # Extract content after "User: "
        user_match = re.search(
            r"</retrieved_memories>\s*\n+User:\s*(.+)", content, re.DOTALL
        )
        if user_match:
            content = user_match.group(1).strip()

    # 2. Handle [Vision Analysis: ...] prefix
    if content.startswith("[Vision Analysis:"):
        # Find the closing bracket and newlines
        vision_match = re.match(
            r"(\[Vision Analysis:.*?\])\s*\n+(.+)", content, re.DOTALL
        )
        if vision_match:
            context_parts.append(vision_match.group(1))
            content = vision_match.group(2).strip()

    # 3. Handle [CSV File Data]...User Query: pattern
    if "[CSV File Data]" in content:
        csv_match = re.search(
            r"\[CSV File Data\](.*?)User Query:\s*(.+)", content, re.DOTALL
        )
        if csv_match:
            context_parts.append(f"[CSV File Data]{csv_match.group(1).strip()}")
            content = csv_match.group(2).strip()

    # 4. Handle [Document Error: ...] prefix (edge case)
    if content.startswith("[Document Error:"):
        error_match = re.match(
            r"(\[Document Error:.*?\])\s*\n+(.+)", content, re.DOTALL
        )
        if error_match:
            context_parts.append(error_match.group(1))
            content = error_match.group(2).strip()

    context = "\n\n".join(context_parts) if context_parts else ""
    return content, context


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for filtering and gathering evaluation data.

    Supports two modes:
    1. Standard mode: Reads from Parquet staging data (MODEL evaluation)
    2. Bypass mode: Passes through pre-uploaded dataset (RAG evaluation BYOI)

    Args:
        event: Configuration from Step Functions
        context: Lambda context

    Returns:
        Dataset metadata and S3 location
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Check for bypass mode (RAG evaluation with pre-uploaded dataset)
    if event.get("skip_filter_step") and event.get("dataset_s3_uri"):
        logger.info("Bypass mode: Using pre-uploaded dataset for RAG evaluation")
        return {
            "dataset_s3_uri": event["dataset_s3_uri"],
            "question_count": event.get("limit", 10),
            "sampling_stats": {
                "total_records": event.get("limit", 10),
                "filtered_records": event.get("limit", 10),
                "sampled_records": event.get("limit", 10),
                "bypass_mode": True,
                "evaluation_type": event.get(
                    "evaluation_type", "RAG_RETRIEVE_AND_GENERATE"
                ),
            },
            # Pass through evaluation_type for CreateEvaluationJob Lambda
            "evaluation_type": event.get(
                "evaluation_type", "RAG_RETRIEVE_AND_GENERATE"
            ),
            "agent_name": event.get("agent_name", "unknown"),
            "metrics": event.get("metrics", []),
        }

    # Standard mode: Read from Parquet staging data
    config = event
    agent_name = config["agent_name"]
    start_date = normalize_date(config["start_date"], is_end_date=False)
    end_date = normalize_date(config["end_date"], is_end_date=True)
    limit = config["limit"]

    logger.info(f"Normalized dates: start={start_date}, end={end_date}")

    # Get context handling configuration (from event or environment variables)
    # strip_context: Extract user question from full prompt (default: True)
    # include_context_as_reference: Put context in referenceResponse field (default: False)
    strip_context = config.get(
        "strip_context", os.environ.get("STRIP_CONTEXT", "true").lower() == "true"
    )
    include_context_as_reference = config.get(
        "include_context_as_reference",
        os.environ.get("INCLUDE_CONTEXT_AS_REFERENCE", "false").lower() == "true",
    )
    logger.info(
        f"Context handling: strip_context={strip_context}, "
        f"include_context_as_reference={include_context_as_reference}"
    )

    # Get S3 bucket from environment
    bucket_name = os.environ.get("STAGING_BUCKET")
    if not bucket_name:
        raise ValueError("STAGING_BUCKET environment variable not set")

    # Step 1: List and read Parquet files from staging
    logger.info(
        f"Reading staging data for agent={agent_name}, date_range={start_date} to {end_date}"
    )
    records = read_staging_data(
        bucket_name=bucket_name,
        agent_name=agent_name,
        start_date=start_date,
        end_date=end_date,
    )

    total_records = len(records)
    logger.info(f"Found {total_records} total records in staging")

    # Step 2: Apply sampling (simple random for MVP, can add stratified later)
    sampled_records = apply_sampling(records, limit)
    sampled_count = len(sampled_records)
    logger.info(f"Sampled {sampled_count} records (limit: {limit})")

    # Step 3: Transform to Bedrock evaluation format
    evaluation_dataset = transform_to_bedrock_format(
        sampled_records,
        agent_name,
        strip_context=strip_context,
        include_context_as_reference=include_context_as_reference,
    )

    # Step 4: Write JSONL to S3
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dataset_key = f"evaluation-datasets/{agent_name}/{timestamp}/dataset.jsonl"
    dataset_s3_uri = write_jsonl_to_s3(
        bucket_name=bucket_name, key=dataset_key, records=evaluation_dataset
    )

    # Step 5: Write sampling stats
    stats = {
        "total_records": total_records,
        "filtered_records": total_records,  # No filtering yet (MVP)
        "sampled_records": sampled_count,
        "timestamp": timestamp,
        "context_handling": {
            "strip_context": strip_context,
            "include_context_as_reference": include_context_as_reference,
        },
    }

    stats_key = f"evaluation-datasets/{agent_name}/{timestamp}/sampling_stats.json"
    write_json_to_s3(bucket_name=bucket_name, key=stats_key, data=stats)

    # Return results to Step Functions
    return {
        "dataset_s3_uri": dataset_s3_uri,
        "question_count": sampled_count,
        "sampling_stats": stats,
    }


def read_staging_data(
    bucket_name: str, agent_name: str, start_date: str, end_date: str
) -> List[Dict[str, Any]]:
    """
    Read Parquet files from S3 staging with hour-level filtering.

    Args:
        bucket_name: S3 bucket name
        agent_name: Agent name for partition filtering
        start_date: Start date (ISO 8601 UTC: YYYY-MM-DDTHH:MM:SSZ)
        end_date: End date (ISO 8601 UTC: YYYY-MM-DDTHH:MM:SSZ)

    Returns:
        List of records from Parquet files (filtered by exact timestamp range)
    """
    records = []

    # Parse ISO 8601 dates (replace Z with +00:00 for fromisoformat compatibility)
    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    # Iterate hour by hour through the range
    current_dt = start_dt.replace(minute=0, second=0, microsecond=0)

    while current_dt <= end_dt:
        # Build Hive-style partition prefix
        prefix = (
            f"staging/agent_name={agent_name}/"
            f"yyyy={current_dt.year}/"
            f"mm={current_dt.month:02d}/"
            f"dd={current_dt.day:02d}/"
            f"hh={current_dt.hour:02d}/"
        )

        logger.info(f"Listing objects in prefix: {prefix}")

        try:
            # List all Parquet files for this hour partition
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

            if "Contents" not in response:
                logger.debug(f"No files found in prefix: {prefix}")
                current_dt += timedelta(hours=1)
                continue

            # Read each Parquet file
            for obj in response["Contents"]:
                key = obj["Key"]

                if not key.endswith(".parquet"):
                    continue

                logger.info(f"Reading Parquet file: {key}")

                # Download Parquet file
                parquet_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
                parquet_bytes = parquet_obj["Body"].read()

                # Read with PyArrow
                table = pq.read_table(BytesIO(parquet_bytes))

                # Convert to list of dicts
                df = table.to_pandas()
                file_records = df.to_dict("records")

                # Filter records by exact timestamp range (for partial hour boundaries)
                for record in file_records:
                    ts = record.get("timestamp")
                    if ts is not None:
                        # pandas timestamp -> python datetime
                        record_dt = (
                            ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                        )
                        if start_dt <= record_dt <= end_dt:
                            records.append(record)
                    else:
                        # Include records without timestamp
                        records.append(record)

                logger.info(f"Read {len(file_records)} records from {key}")

        except Exception as e:
            logger.error(f"Error reading partition {prefix}: {str(e)}", exc_info=True)

        current_dt += timedelta(hours=1)

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
    agent_name: str,
    strip_context: bool = True,
    include_context_as_reference: bool = False,
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
      "referenceResponse": "..." (optional),
      "category": "budgeting" (optional)
    }

    Args:
        records: Staging records (from Parquet)
        agent_name: Agent identifier
        strip_context: If True, extract user question from full prompt (default: True)
        include_context_as_reference: If True and strip_context=True,
                                      put extracted context in referenceResponse (default: False)

    Returns:
        List of records in Bedrock format
    """
    evaluation_records = []

    for record in records:
        # Extract prompt and response from record
        full_prompt = record.get("prompt", "")
        response = record.get("response", "")

        # Skip records with missing data
        if not full_prompt or not response:
            logger.warning(
                f"Skipping record with missing prompt/response: {record.get('request_id')}"
            )
            continue

        # Determine prompt and context based on configuration
        if strip_context:
            user_question, context = extract_user_question(full_prompt)
            # Fallback: if extraction returned empty, use full prompt
            prompt = user_question if user_question.strip() else full_prompt
            if prompt != full_prompt:
                logger.debug(
                    f"Extracted user question: '{prompt[:100]}...' from full prompt"
                )
        else:
            prompt = full_prompt
            context = ""

        # Build Bedrock evaluation record
        eval_record = {
            "prompt": prompt,
            "modelResponses": [{"response": response, "modelIdentifier": agent_name}],
        }

        # Optionally add context as referenceResponse
        if strip_context and include_context_as_reference and context:
            eval_record["referenceResponse"] = context

        # Add optional category if available
        if "category" in record and record["category"]:
            eval_record["category"] = record["category"]

        evaluation_records.append(eval_record)

    return evaluation_records


def write_jsonl_to_s3(bucket_name: str, key: str, records: List[Dict[str, Any]]) -> str:
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
    jsonl_content = "\n".join(jsonl_lines)

    # Upload to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=jsonl_content.encode("utf-8"),
        ContentType="application/x-ndjson",
        ServerSideEncryption="AES256",
    )

    s3_uri = f"s3://{bucket_name}/{key}"
    logger.info(f"Wrote {len(records)} records to {s3_uri}")

    return s3_uri


def write_json_to_s3(bucket_name: str, key: str, data: Dict[str, Any]) -> str:
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
        Body=json_content.encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    s3_uri = f"s3://{bucket_name}/{key}"
    logger.info(f"Wrote JSON to {s3_uri}")

    return s3_uri
