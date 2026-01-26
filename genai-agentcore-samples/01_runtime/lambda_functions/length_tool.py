"""
Lambda function handler for text length calculation tool.
This is a dummy tool for testing AgentCore Gateway integration.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for text length calculation tool.
    
    Expected input format:
    {
        "text": "hello world"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": "The text '{text}' has {length} characters. (This is a dummy calculation for testing AgentCore deployment)"
    }
    """
    try:
        # Parse input - Gateway may pass arguments in different formats
        if isinstance(event, str):
            event = json.loads(event)
        
        # Extract text from event
        text = event.get("text") or event.get("arguments", {}).get("text")
        
        if text is None:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Missing required parameter: text"
                })
            }
        
        # Calculate length
        length = len(str(text))
        
        # Generate response
        result = f"The text '{text}' has {length} characters. (This is a dummy calculation for testing AgentCore deployment)"
        
        logger.info(f"Length tool invoked for text: {text[:50]}... (length: {length})")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "result": result,
                "text": text,
                "length": length
            })
        }
        
    except Exception as e:
        logger.error(f"Error in length tool: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Internal error: {str(e)}"
            })
        }

