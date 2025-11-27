"""
Process Results Lambda - Step Functions Task

Downloads evaluation job output from S3 and extracts metrics summary.
Creates aggregated results for downstream analysis.

Input (from Step Functions):
{
  "job_arn": "arn:aws:bedrock:...",
  "job_name": "eval-...",
  "status": "Completed",
  "output_s3_uri": "s3://bucket/evaluation-results/agent/timestamp/",
  "agent_name": "my-agent",
  "metrics": ["Builtin.Correctness"],
  ...
}

Output:
{
  ...input fields,
  "results": {
    "metrics": [
      {
        "name": "Builtin.Correctness",
        "average_score": 0.95,
        "sample_count": 10
      }
    ],
    "output_files": ["s3://..."],
    "processed_at": "2025-11-25T12:00:00Z"
  }
}
"""

import boto3
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process evaluation job results and extract metrics.

    Args:
        event: Job metadata including output location
        context: Lambda context

    Returns:
        Event with added results summary
    """
    logger.info(f"Received event: {json.dumps(event)}")

    output_s3_uri = event.get('output_s3_uri')
    agent_name = event.get('agent_name', 'unknown')
    job_name = event.get('job_name', 'unknown')

    if not output_s3_uri:
        logger.error("No output_s3_uri provided")
        return {
            **event,
            'results': {
                'error': 'No output_s3_uri provided',
                'processed_at': datetime.utcnow().isoformat() + 'Z'
            }
        }

    # Parse S3 URI
    parsed = urlparse(output_s3_uri)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip('/')

    logger.info(f"Processing results from s3://{bucket}/{prefix}")

    try:
        # List output files
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )

        if 'Contents' not in response:
            logger.warning(f"No output files found in {output_s3_uri}")
            return {
                **event,
                'results': {
                    'error': 'No output files found',
                    'processed_at': datetime.utcnow().isoformat() + 'Z'
                }
            }

        output_files = [f"s3://{bucket}/{obj['Key']}" for obj in response['Contents']]
        logger.info(f"Found {len(output_files)} output files")

        # Find and process the JSONL results file
        metrics_summary = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.jsonl'):
                metrics_summary = process_jsonl_results(bucket, key)
                break

        # Build summary
        results = {
            'metrics': metrics_summary,
            'output_files': output_files,
            'processed_at': datetime.utcnow().isoformat() + 'Z',
            'job_name': job_name
        }

        # Write summary to S3
        summary_key = f"{prefix}summary.json"
        write_summary_to_s3(bucket, summary_key, results, event)

        return {
            **event,
            'results': results
        }

    except Exception as e:
        logger.error(f"Error processing results: {str(e)}", exc_info=True)
        return {
            **event,
            'results': {
                'error': str(e),
                'processed_at': datetime.utcnow().isoformat() + 'Z'
            }
        }


def process_jsonl_results(bucket: str, key: str) -> List[Dict[str, Any]]:
    """
    Process JSONL results file and extract metrics.

    Args:
        bucket: S3 bucket
        key: S3 key

    Returns:
        List of metric summaries
    """
    logger.info(f"Processing JSONL results: s3://{bucket}/{key}")

    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')

    metrics_data = {}

    for line in content.strip().split('\n'):
        if not line:
            continue

        try:
            record = json.loads(line)

            # Extract metric scores from evaluation output
            # Bedrock output format: evaluationResults[].metricResults[].name, score
            eval_results = record.get('evaluationResults', [])
            for eval_result in eval_results:
                metric_results = eval_result.get('metricResults', [])
                for metric in metric_results:
                    name = metric.get('name', 'Unknown')
                    score = metric.get('score')

                    if score is not None:
                        if name not in metrics_data:
                            metrics_data[name] = {'scores': [], 'count': 0}
                        metrics_data[name]['scores'].append(score)
                        metrics_data[name]['count'] += 1

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse line: {e}")
            continue

    # Calculate averages
    metrics_summary = []
    for name, data in metrics_data.items():
        avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
        metrics_summary.append({
            'name': name,
            'average_score': round(avg_score, 4),
            'sample_count': data['count']
        })

    logger.info(f"Processed {len(metrics_summary)} metrics")
    return metrics_summary


def write_summary_to_s3(bucket: str, key: str, results: Dict, event: Dict) -> None:
    """
    Write results summary to S3.

    Args:
        bucket: S3 bucket
        key: S3 key
        results: Results summary
        event: Original event for context
    """
    summary = {
        'job_arn': event.get('job_arn'),
        'job_name': event.get('job_name'),
        'agent_name': event.get('agent_name'),
        'dataset_s3_uri': event.get('dataset_s3_uri'),
        'question_count': event.get('question_count'),
        'results': results
    }

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(summary, indent=2).encode('utf-8'),
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )

    logger.info(f"Wrote summary to s3://{bucket}/{key}")
