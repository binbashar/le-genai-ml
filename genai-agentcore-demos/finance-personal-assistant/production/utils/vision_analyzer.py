"""Generic vision analysis for financial documents.

This module provides vision analysis capabilities for images, automatically
detecting financial documents (receipts, invoices) and extracting structured data.
"""

import json
import logging
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

from config import get_region

logger = logging.getLogger(__name__)

# Vision model configuration (simplified for reliability)
VISION_MODEL_ID = "us.amazon.nova-premier-v1:0"
VISION_MAX_TOKENS = 4096
VISION_TEMPERATURE = 0.1

# Internal prompt for vision model (not user-facing)
VISION_ANALYSIS_PROMPT = """Analyze this image and determine if it's a financial document.

If it's a RECEIPT or INVOICE:
- Extract: merchant name, date, total amount, line items (with prices), suggested expense category
- Return JSON with this structure:
{
    "type": "receipt",
    "summary": "Brief description of the document",
    "data": {
        "merchant": "Store name",
        "date": "YYYY-MM-DD",
        "total": 0.00,
        "items": ["Item 1: $XX.XX", "Item 2: $XX.XX"],
        "category": "Category name (e.g., Groceries, Dining, Transportation)"
    }
}

If it's UNKNOWN or not a financial document:
- Return JSON: {"type": "unknown", "summary": "Image content not recognized as a financial document"}

Return ONLY valid JSON, no markdown, no explanatory text."""


def analyze_image(image_base64: str) -> Dict[str, Any]:
    """
    Analyze image using Bedrock vision model.

    This function performs automatic vision analysis on uploaded images,
    detecting financial documents and extracting structured data.

    Args:
        image_base64: Base64-encoded image string (JPEG/PNG)

    Returns:
        Dictionary with standardized structure:
        {
            "status": "success" | "unknown" | "error",
            "keywords": ["receipt", "invoice"] or [],
            "summary": "Human-readable description",
            "data": {...}  # Structured data if applicable, empty dict otherwise
        }

    Examples:
        >>> result = analyze_image(base64_image)
        >>> if result["status"] == "success":
        ...     print(result["data"]["total"])
    """
    try:
        # Build Nova messages-v1 format
        request_body = {
            "schemaVersion": "messages-v1",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": "jpeg",
                            "source": {"bytes": image_base64}
                        }
                    },
                    {"text": VISION_ANALYSIS_PROMPT}
                ]
            }],
            "inferenceConfig": {
                "maxTokens": VISION_MAX_TOKENS,
                "temperature": VISION_TEMPERATURE
            }
        }

        # Invoke Bedrock Runtime API
        client = boto3.client("bedrock-runtime", region_name=get_region())
        logger.info(f"Invoking vision model: {VISION_MODEL_ID}")

        response = client.invoke_model(
            modelId=VISION_MODEL_ID,
            body=json.dumps(request_body)
        )

        # Parse response (Nova format)
        response_body = json.loads(response["body"].read())
        content = response_body["output"]["message"]["content"][0]["text"]

        logger.debug(f"Vision model response: {content}")

        # Extract and parse JSON from response
        parsed = _extract_json(content)

        if not parsed:
            logger.warning("Failed to extract JSON from vision response")
            return {
                "status": "error",
                "keywords": [],
                "summary": "Failed to parse vision model response",
                "data": {}
            }

        # Normalize response format
        return _normalize_response(parsed)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Bedrock API error ({error_code}): {error_msg}")

        return {
            "status": "error",
            "keywords": [],
            "summary": f"Vision API error: {error_code}",
            "data": {}
        }

    except Exception as e:
        # Fail gracefully for any unexpected errors
        logger.error(f"Unexpected error in vision analysis: {e}", exc_info=True)
        return {
            "status": "error",
            "keywords": [],
            "summary": f"Vision analysis failed: {str(e)}",
            "data": {}
        }


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON object from text response.

    Handles cases where model returns markdown code blocks or
    additional text around the JSON.

    Args:
        text: Response text that may contain JSON

    Returns:
        Parsed JSON dict, or None if extraction fails
    """
    try:
        # Try direct parsing first
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    if "```json" in text:
        try:
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    # Try extracting from generic code block
    if "```" in text:
        try:
            json_str = text.split("```")[1].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    # Try finding JSON-like structure with regex as last resort
    import re
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not extract JSON from text: {text[:200]}")
    return None


def _normalize_response(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize vision model response to standard format.

    Args:
        parsed: Raw JSON response from vision model

    Returns:
        Normalized response dict with standard keys
    """
    doc_type = parsed.get("type", "unknown")

    if doc_type == "unknown":
        return {
            "status": "unknown",
            "keywords": [],
            "summary": parsed.get("summary", "Image not recognized as a financial document"),
            "data": {}
        }
    else:
        # Success case - financial document detected
        keywords = [doc_type]

        # Add additional keywords based on data
        data = parsed.get("data", {})
        if "category" in data:
            keywords.append(data["category"].lower())

        return {
            "status": "success",
            "keywords": keywords,
            "summary": parsed.get("summary", f"{doc_type.title()} detected"),
            "data": data
        }
