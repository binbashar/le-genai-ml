"""
PII Scrubber - Basic regex-based PII detection and redaction (MVP)

Removes common PII patterns before S3 storage:
- Social Security Numbers (SSN): 123-45-6789
- Email addresses: user@example.com
- Phone numbers: (555) 123-4567, 555-123-4567
- Credit card numbers: 1234-5678-9012-3456

Future enhancements (post-MVP):
- AWS Bedrock Guardrails for ML-based detection
- AWS Comprehend for entity recognition
"""

import re
from typing import Dict, Any


def scrub_pii_basic(text: str) -> str:
    """
    Remove common PII patterns using regex (MVP approach).

    Args:
        text: Input text that may contain PII

    Returns:
        Text with PII patterns replaced with redaction markers
    """
    if not text or not isinstance(text, str):
        return text

    # SSN: 123-45-6789 or 123456789
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", text)
    text = re.sub(r"\b\d{9}\b", "[SSN_REDACTED]", text)

    # Email: user@example.com
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]", text
    )

    # Phone: (555) 123-4567, 555-123-4567, 555.123.4567
    text = re.sub(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]", text)

    # Credit Card: 1234-5678-9012-3456, 1234 5678 9012 3456
    text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CC_REDACTED]", text)

    return text


def scrub_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply PII scrubbing to all text fields in a log record.

    Scrubs:
    - input.prompt
    - output.message.content[].text (for text content blocks)

    Args:
        record: Bedrock invocation log record

    Returns:
        Record with PII redacted from text fields
    """
    # Scrub input prompt
    if "input" in record and "prompt" in record["input"]:
        record["input"]["prompt"] = scrub_pii_basic(record["input"]["prompt"])

    # Scrub output message content
    if "output" in record and "message" in record["output"]:
        message = record["output"]["message"]
        if "content" in message and isinstance(message["content"], list):
            for content_block in message["content"]:
                if content_block.get("type") == "text" and "text" in content_block:
                    content_block["text"] = scrub_pii_basic(content_block["text"])

    return record
