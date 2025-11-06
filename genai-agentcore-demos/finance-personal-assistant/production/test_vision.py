#!/usr/bin/env python3
"""Test script to verify Nova Premier vision API format."""

import base64
import json
import sys
from pathlib import Path

import boto3
from config import get_region

# Test with receipt image
RECEIPT_PATH = Path.home() / "Pictures" / "receipt.png"

# Vision model configuration
VISION_MODEL_ID = "us.amazon.nova-premier-v1:0"
VISION_MAX_TOKENS = 4096
VISION_TEMPERATURE = 0.1

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


def test_vision_analysis():
    """Test vision analysis with correct Nova API format."""
    print(f"Testing vision analysis with: {RECEIPT_PATH}")

    if not RECEIPT_PATH.exists():
        print(f"ERROR: Receipt not found at {RECEIPT_PATH}")
        sys.exit(1)

    # Read and encode image
    with open(RECEIPT_PATH, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    print(f"Image encoded: {len(image_base64)} bytes")

    # Build request with CORRECT format (text, not inputText)
    request_body = {
        "schemaVersion": "messages-v1",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": "png",  # Changed to png since receipt is .png
                        "source": {"bytes": image_base64}
                    }
                },
                {"text": VISION_ANALYSIS_PROMPT}  # CORRECT: "text" not "inputText"
            ]
        }],
        "inferenceConfig": {
            "maxTokens": VISION_MAX_TOKENS,
            "temperature": VISION_TEMPERATURE
        }
    }

    print(f"\nInvoking model: {VISION_MODEL_ID}")
    print(f"Region: {get_region()}")

    # Invoke Bedrock
    client = boto3.client("bedrock-runtime", region_name=get_region())

    try:
        response = client.invoke_model(
            modelId=VISION_MODEL_ID,
            body=json.dumps(request_body)
        )

        # Parse response
        response_body = json.loads(response["body"].read())
        content = response_body["output"]["message"]["content"][0]["text"]

        print("\n✅ SUCCESS! Raw response:")
        print(content)

        # Try to parse JSON
        try:
            parsed = json.loads(content)
            print("\n✅ Parsed JSON:")
            print(json.dumps(parsed, indent=2))

            if parsed.get("type") == "receipt":
                print("\n✅ Receipt detected!")
                print(f"Merchant: {parsed['data'].get('merchant')}")
                print(f"Total: ${parsed['data'].get('total')}")
                print(f"Items: {len(parsed['data'].get('items', []))}")
        except json.JSONDecodeError as e:
            print(f"\n⚠️ Could not parse JSON: {e}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_vision_analysis()
