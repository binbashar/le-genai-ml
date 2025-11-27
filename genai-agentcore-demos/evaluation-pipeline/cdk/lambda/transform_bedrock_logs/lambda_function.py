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
4. Apply PII scrubbing
5. Transform to flat Parquet schema
6. Write Parquet directly to S3 with partitioning
7. Return "Dropped" to Firehose (records already written to S3)
"""

import base64
import gzip
import json
import logging
from typing import Dict, Any, List

from pii_scrubber import scrub_record
from schema import extract_structured_record
from parquet_storage import ParquetStorageManager, get_bucket_name_from_env

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3/Parquet storage manager
storage_manager = None


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

            # Apply PII scrubbing
            scrubbed_log = scrub_record(bedrock_log)

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
