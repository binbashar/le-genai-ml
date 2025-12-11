"""
Kinesis Firehose Transformation Lambda - Bedrock Log Processing

This Lambda function processes Bedrock invocation logs from CloudWatch Logs
via Kinesis Firehose, applies PII scrubbing, and writes Parquet files
directly to S3 with partitioning.

Firehose Integration:
- Input: Firehose records (base64-encoded CloudWatch Logs data)
- Output: "Dropped" status (Lambda writes directly to S3, bypasses Firehose writes)
- Timeout: 3 minutes (Firehose maximum)

Processing Steps:
1. Decode base64 Firehose record
2. Parse CloudWatch Logs format
3. Extract Bedrock invocation log
4. Apply PII scrubbing (defense-in-depth: regex + Bedrock Guardrails)
5. Transform to flat Parquet schema
6. Write Parquet directly to S3 with partitioning
7. Return "Dropped" to Firehose (records already written to S3)

PII Filtering Modes (controlled by environment variables):
- GUARDRAILS_ENABLED=true + PII_REGEX_ENABLED=true: Defense-in-depth (regex + Guardrails)
- GUARDRAILS_ENABLED=true + PII_REGEX_ENABLED=false: Guardrails only (isolated testing)
- GUARDRAILS_ENABLED=false + PII_REGEX_ENABLED=true: Regex only (free baseline)
- GUARDRAILS_ENABLED=false + PII_REGEX_ENABLED=false: Pass-through (no filtering)
"""

import base64
import gzip
import json
import logging
import os
from typing import Any, Dict, List

from parquet_storage import ParquetStorageManager, get_bucket_name_from_env
from pii_scrubber import scrub_record, scrub_record_guardrails_only, scrub_record_with_guardrails
from schema import extract_structured_record

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3/Parquet storage manager
storage_manager = None

# PII filtering configuration (from environment variables)
GUARDRAILS_ENABLED = os.environ.get("GUARDRAILS_ENABLED", "false").lower() == "true"
PII_REGEX_ENABLED = os.environ.get("PII_REGEX_ENABLED", "true").lower() == "true"
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "")


def lambda_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Kinesis Firehose transformation handler.

    Processes records, writes Parquet to S3, and returns "Dropped" status
    to Firehose (since Lambda already wrote to S3).

    Args:
        event: Firehose transformation event
            {
                "invocationId": "...",
                "deliveryStreamArn": "...",
                "region": "us-west-2",
                "records": [
                    {
                        "recordId": "...",
                        "data": "base64-encoded-cloudwatch-logs",
                        "approximateArrivalTimestamp": 1234567890
                    }
                ]
            }
        context: Lambda context

    Returns:
        Firehose transformation result (all records marked as "Dropped"):
            {
                "records": [
                    {
                        "recordId": "...",
                        "result": "Dropped",
                        "data": "base64-encoded-original-data"
                    }
                ]
            }
    """
    logger.info(f"Processing {len(event['records'])} records from Firehose")
    logger.info(f"PII filtering: Guardrails={'enabled' if GUARDRAILS_ENABLED else 'disabled'}, Regex={'enabled' if PII_REGEX_ENABLED else 'disabled'}")

    # Initialize storage manager (lazy initialization)
    global storage_manager
    if storage_manager is None:
        bucket_name = get_bucket_name_from_env()
        storage_manager = ParquetStorageManager(bucket_name, prefix="staging")

    # Process all records and collect structured data
    structured_records = []
    output_records = []

    for record in event["records"]:
        record_id = record["recordId"]
        encoded_data = record["data"]

        try:
            # Decode Firehose record (base64 → bytes)
            decoded_data = base64.b64decode(encoded_data)

            # Parse CloudWatch Logs format (gzip-compressed JSON)
            cloudwatch_log = _parse_cloudwatch_logs(decoded_data)

            if not cloudwatch_log:
                logger.warning(f"Record {record_id}: No valid CloudWatch log found")
                output_records.append(
                    {"recordId": record_id, "result": "Dropped", "data": encoded_data}
                )
                continue

            # Extract Bedrock invocation log
            bedrock_log = _extract_bedrock_log(cloudwatch_log)

            if not bedrock_log:
                logger.warning(f"Record {record_id}: No valid Bedrock log found")
                output_records.append(
                    {"recordId": record_id, "result": "Dropped", "data": encoded_data}
                )
                continue

            # Apply PII scrubbing based on configuration
            if GUARDRAILS_ENABLED and PII_REGEX_ENABLED and GUARDRAIL_ID and GUARDRAIL_VERSION:
                # Defense-in-depth: regex + Guardrails
                scrubbed_log = scrub_record_with_guardrails(
                    bedrock_log,
                    guardrail_id=GUARDRAIL_ID,
                    guardrail_version=GUARDRAIL_VERSION,
                )
            elif GUARDRAILS_ENABLED and GUARDRAIL_ID and GUARDRAIL_VERSION:
                # Guardrails only (isolated testing)
                scrubbed_log = scrub_record_guardrails_only(
                    bedrock_log,
                    guardrail_id=GUARDRAIL_ID,
                    guardrail_version=GUARDRAIL_VERSION,
                )
            elif PII_REGEX_ENABLED:
                # Regex only (free baseline)
                scrubbed_log = scrub_record(bedrock_log)
            else:
                # Pass-through (no PII filtering)
                scrubbed_log = bedrock_log

            # Transform to structured schema
            structured_record = extract_structured_record(scrubbed_log)
            structured_records.append(structured_record)

            # Return "Dropped" to Firehose (Lambda writes to S3 directly)
            output_records.append(
                {"recordId": record_id, "result": "Dropped", "data": encoded_data}
            )

            logger.info(f"Record {record_id}: Processed successfully")

        except Exception as e:
            logger.error(
                f"Record {record_id}: Processing failed - {str(e)}", exc_info=True
            )
            output_records.append(
                {
                    "recordId": record_id,
                    "result": "ProcessingFailed",
                    "data": encoded_data,
                }
            )

    # Write all structured records to S3 as Parquet (batched by partition)
    if structured_records:
        try:
            result = storage_manager.write_batch(structured_records)
            logger.info(
                f"Parquet write complete: {result['successful']}/{result['total']} successful, "
                f"{result['failed']} failed"
            )
        except Exception as e:
            logger.error(f"Failed to write Parquet batch: {str(e)}", exc_info=True)

    logger.info(f"Transformation complete: {len(output_records)} records processed")
    return {"records": output_records}


def _parse_cloudwatch_logs(data: bytes) -> Dict[str, Any]:
    """
    Parse CloudWatch Logs format from Firehose.

    CloudWatch Logs format (gzip-compressed JSON):
    {
        "messageType": "DATA_MESSAGE",
        "owner": "123456789012",
        "logGroup": "bedrock-model-invocations",
        "logStream": "...",
        "subscriptionFilters": ["..."],
        "logEvents": [
            {
                "id": "...",
                "timestamp": 1234567890,
                "message": "{...}"  # Bedrock log as JSON string
            }
        ]
    }

    Args:
        data: Gzip-compressed CloudWatch Logs data

    Returns:
        Parsed CloudWatch log or empty dict if parsing fails
    """
    try:
        # Decompress gzip
        decompressed = gzip.decompress(data)

        # Parse JSON
        cloudwatch_log = json.loads(decompressed)

        return cloudwatch_log

    except Exception as e:
        logger.warning(f"Failed to parse CloudWatch Logs format: {str(e)}")
        return {}


def _extract_bedrock_log(cloudwatch_log: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract Bedrock invocation log from CloudWatch Logs event.

    Args:
        cloudwatch_log: Parsed CloudWatch Logs event

    Returns:
        Bedrock invocation log or empty dict if extraction fails
    """
    try:
        # Extract first log event
        log_events = cloudwatch_log.get("logEvents", [])
        if not log_events:
            return {}

        first_event = log_events[0]
        message = first_event.get("message", "")

        # Parse message as JSON (Bedrock invocation log)
        bedrock_log = json.loads(message)

        return bedrock_log

    except Exception as e:
        logger.warning(f"Failed to extract Bedrock log: {str(e)}")
        return {}
