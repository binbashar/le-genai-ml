"""
Parquet Storage Manager - Incremental S3 writes with partitioning

Manages Parquet file creation and incremental storage in S3:
1. Batches records by partition key (agent_name + yyyy/mm/dd/hh)
2. Creates Parquet files with PyArrow
3. Writes directly to S3 with proper directory structure
4. Handles incremental appends (creates new files, doesn't append to existing)

Directory Structure (Hive-style partitioning):
s3://bucket/staging/
    agent_name=nova-lite/
        yyyy=2025/mm=11/dd=24/hh=14/
            part-001.parquet
        yyyy=2025/mm=11/dd=24/hh=15/
            part-001.parquet
    agent_name=claude-sonnet/
        yyyy=2025/mm=11/dd=24/hh=09/
            part-001.parquet
"""

import io
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

from schema import BEDROCK_LOG_SCHEMA

logger = logging.getLogger(__name__)


class ParquetStorageManager:
    """
    Manages Parquet file creation and S3 storage with partitioning.
    """

    def __init__(self, bucket_name: str, prefix: str = "staging"):
        """
        Initialize Parquet storage manager.

        Args:
            bucket_name: S3 bucket name
            prefix: S3 prefix for staging data (default: "staging")
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client('s3')

    def write_batch(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Write batch of records to S3 as Parquet files.

        Groups records by partition key (agent_name + date) and writes
        separate Parquet files for each partition.

        Args:
            records: List of structured records (from schema.extract_structured_record)

        Returns:
            Dict with counts: {'total': N, 'successful': M, 'failed': K}
        """
        if not records:
            return {'total': 0, 'successful': 0, 'failed': 0}

        # Group records by partition key
        partitions = self._group_by_partition(records)

        total = len(records)
        successful = 0
        failed = 0

        # Write each partition to S3
        for partition_key, partition_records in partitions.items():
            try:
                self._write_partition(partition_key, partition_records)
                successful += len(partition_records)
                logger.info(f"Wrote {len(partition_records)} records to partition: {partition_key}")
            except Exception as e:
                logger.error(f"Failed to write partition {partition_key}: {str(e)}", exc_info=True)
                failed += len(partition_records)

        return {'total': total, 'successful': successful, 'failed': failed}

    def _group_by_partition(self, records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group records by partition key (agent_name + yyyy/mm/dd/hh).

        Args:
            records: List of structured records

        Returns:
            Dict mapping partition keys to record lists
        """
        partitions = {}

        for record in records:
            agent_name = record.get('_agent_name', 'unknown')
            date = record.get('_date', datetime.utcnow().strftime('%Y-%m-%d'))
            hour = record.get('_hour', '00')

            # Hive-style partitioning: yyyy=YYYY/mm=MM/dd=DD/hh=HH
            year, month, day = date.split('-')
            partition_key = f"agent_name={agent_name}/yyyy={year}/mm={month}/dd={day}/hh={hour}"

            if partition_key not in partitions:
                partitions[partition_key] = []

            partitions[partition_key].append(record)

        return partitions

    def _write_partition(self, partition_key: str, records: List[Dict[str, Any]]) -> None:
        """
        Write records to a Parquet file in S3.

        Creates a new Parquet file with timestamp-based naming for incremental storage.

        Args:
            partition_key: Partition path (e.g., "agent_name=nova-lite/yyyy=2025/mm=11/dd=24/hh=14")
            records: List of structured records for this partition
        """
        # Generate unique filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')
        filename = f"part-{timestamp}.parquet"

        # Full S3 key
        s3_key = f"{self.prefix}/{partition_key}/{filename}"

        # Convert records to PyArrow Table
        table = self._records_to_table(records)

        # Write Parquet to in-memory buffer
        buffer = io.BytesIO()
        pq.write_table(
            table,
            buffer,
            compression='snappy',  # Good balance of compression and speed
            use_dictionary=True,    # Efficient encoding for repeated strings
            write_statistics=True,  # Enable column statistics for query optimization
        )

        # Upload to S3
        buffer.seek(0)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType='application/parquet',
            ServerSideEncryption='AES256',
        )

        logger.info(f"Uploaded Parquet file: s3://{self.bucket_name}/{s3_key} ({len(records)} records)")

    def _records_to_table(self, records: List[Dict[str, Any]]) -> pa.Table:
        """
        Convert list of records to PyArrow Table.

        Args:
            records: List of structured records

        Returns:
            PyArrow Table matching BEDROCK_LOG_SCHEMA
        """
        # Extract columns from records
        columns = {field.name: [] for field in BEDROCK_LOG_SCHEMA}

        for record in records:
            for field in BEDROCK_LOG_SCHEMA:
                value = record.get(field.name)

                # Handle None values and type conversions
                if value is None:
                    if pa.types.is_string(field.type):
                        value = ''
                    elif pa.types.is_integer(field.type):
                        value = 0
                    elif pa.types.is_timestamp(field.type):
                        value = None  # Allow null timestamps

                columns[field.name].append(value)

        # Create PyArrow arrays for each column
        arrays = []
        for field in BEDROCK_LOG_SCHEMA:
            column_data = columns[field.name]

            # Convert to PyArrow array with proper type
            if pa.types.is_timestamp(field.type):
                # Parse ISO timestamp strings
                parsed_timestamps = []
                for ts in column_data:
                    if ts:
                        try:
                            # Parse ISO format: 2025-11-24T12:34:56.789Z
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            parsed_timestamps.append(dt)
                        except Exception:
                            parsed_timestamps.append(None)
                    else:
                        parsed_timestamps.append(None)

                arrays.append(pa.array(parsed_timestamps, type=field.type))
            else:
                arrays.append(pa.array(column_data, type=field.type))

        return pa.Table.from_arrays(arrays, schema=BEDROCK_LOG_SCHEMA)


def get_bucket_name_from_env() -> str:
    """
    Get S3 bucket name from environment variable.

    Returns:
        S3 bucket name

    Raises:
        ValueError: If BUCKET_NAME not set
    """
    bucket_name = os.environ.get('BUCKET_NAME')
    if not bucket_name:
        raise ValueError("BUCKET_NAME environment variable not set")
    return bucket_name
