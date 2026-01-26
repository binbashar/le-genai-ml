"""
Lambda function handler for weather tool.
This is a dummy tool for testing AgentCore Gateway integration.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for weather tool.
    
    Expected input format:
    {
        "location": "New York"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": "The weather in {location} is sunny and 72°F. (This is dummy data for testing AgentCore deployment)"
    }
    """
    try:
        # Parse input - Gateway may pass arguments in different formats
        if isinstance(event, str):
            event = json.loads(event)
        
        # Extract location from event
        location = event.get("location") or event.get("arguments", {}).get("location")
        
        if not location:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Missing required parameter: location"
                })
            }
        
        # Generate dummy weather response
        result = f"The weather in {location} is sunny and 72°F. (This is dummy data for testing AgentCore deployment)"
        
        logger.info(f"Weather tool invoked for location: {location}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "result": result,
                "location": location
            })
        }
        
    except Exception as e:
        logger.error(f"Error in weather tool: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Internal error: {str(e)}"
            })
        }

