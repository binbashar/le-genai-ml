"""
MVP Lambda - Echo Configuration

Goal: Test that Step Functions can pass configuration to Lambda and receive response
This is the absolute minimum to test connectivity before building real logic.
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Echo configuration back to Step Functions

    Input: Configuration dict from Step Functions
    Output: Same configuration + validation metadata
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Extract configuration
    config = event

    # Validate required fields
    required_fields = ['agent_name', 'start_date', 'end_date', 'limit', 'metrics']
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'error': error_msg,
            'received_config': config
        }

    # Success response
    response = {
        'statusCode': 200,
        'message': 'Configuration received and validated',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'config': config,
        'validation': {
            'agent_name': config['agent_name'],
            'date_range': f"{config['start_date']} to {config['end_date']}",
            'limit': config['limit'],
            'metrics_count': len(config['metrics'])
        }
    }

    logger.info(f"Returning response: {json.dumps(response)}")
    return response
