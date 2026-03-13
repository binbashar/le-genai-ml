"""
PII Scrubber - Defense-in-depth PII detection and redaction

Implements two-layer PII filtering:
1. Regex-based detection (fast, free) - catches common patterns
2. AWS Bedrock Guardrails (ML-based, paid) - catches sophisticated patterns

Supported PII types (30+ via Guardrails):
- General: NAME, EMAIL, PHONE, ADDRESS, AGE, USERNAME, PASSWORD
- Finance: CREDIT_CARD, PIN, BANK_ACCOUNT, SSN
- IT: IP_ADDRESS, AWS_ACCESS_KEY, AWS_SECRET_KEY
- Regional: CA, UK, US specific identifiers

Pipeline: Input → Regex Scrub → Guardrails API → Output

Error handling: Fail-safe - if Guardrails API fails, regex-scrubbed data is used.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# =============================================================================
# Bedrock Guardrails Integration
# =============================================================================


def apply_guardrail_filter(
    text: str,
    guardrail_id: str,
    guardrail_version: str,
    source: str = "OUTPUT",
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply Bedrock Guardrails for ML-based PII detection and anonymization.

    Uses the ApplyGuardrail API to detect and mask PII with type-specific tokens
    like {NAME}, {EMAIL}, {US_SOCIAL_SECURITY_NUMBER}.

    Args:
        text: Input text that may contain PII
        guardrail_id: Bedrock Guardrail ID
        guardrail_version: Guardrail version (use published version for production)
        source: "INPUT" for user prompts, "OUTPUT" for model responses
        region: AWS region (defaults to AWS_REGION env var or us-west-2)

    Returns:
        {
            "text": "filtered text or original if no PII found",
            "intervened": bool,  # True if guardrail modified the text
            "pii_detected": [...],  # List of detected PII entities
            "error": None or str  # Error message if API failed
        }
    """
    if not text or not isinstance(text, str):
        return {
            "text": text,
            "intervened": False,
            "pii_detected": [],
            "error": None,
        }

    if not guardrail_id or not guardrail_version:
        return {
            "text": text,
            "intervened": False,
            "pii_detected": [],
            "error": "Guardrail ID or version not configured",
        }

    # Initialize Bedrock Runtime client
    region_name = region or os.environ.get("AWS_REGION", "us-west-2")
    try:
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=region_name)
    except Exception as e:
        logger.warning(f"Failed to create Bedrock Runtime client: {e}")
        return {
            "text": text,
            "intervened": False,
            "pii_detected": [],
            "error": str(e),
        }

    try:
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source=source,
            content=[{"text": {"text": text}}],
        )

        action = response.get("action", "NONE")
        outputs = response.get("outputs", [])
        assessments = response.get("assessments", [])

        # Extract PII entities from assessments
        pii_detected = []
        for assessment in assessments:
            sensitive_policy = assessment.get("sensitiveInformationPolicy", {})
            pii_entities = sensitive_policy.get("piiEntities", [])
            for entity in pii_entities:
                pii_detected.append(
                    {
                        "type": entity.get("type"),
                        "match": entity.get("match"),
                        "action": entity.get("action"),
                    }
                )

        # Get filtered text
        if action == "GUARDRAIL_INTERVENED" and outputs:
            filtered_text = outputs[0].get("text", text)
            # Remove trailing newline that Bedrock sometimes adds
            if filtered_text.endswith("\n") and not text.endswith("\n"):
                filtered_text = filtered_text.rstrip("\n")
            return {
                "text": filtered_text,
                "intervened": True,
                "pii_detected": pii_detected,
                "error": None,
            }
        else:
            # No intervention - return original text
            return {
                "text": text,
                "intervened": False,
                "pii_detected": pii_detected,
                "error": None,
            }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"Guardrails API error ({error_code}): {error_msg}")
        return {
            "text": text,
            "intervened": False,
            "pii_detected": [],
            "error": f"{error_code}: {error_msg}",
        }
    except Exception as e:
        logger.warning(f"Unexpected error calling Guardrails API: {e}")
        return {
            "text": text,
            "intervened": False,
            "pii_detected": [],
            "error": str(e),
        }


def scrub_text_with_guardrails(
    text: str,
    guardrail_id: str,
    guardrail_version: str,
    source: str = "OUTPUT",
) -> str:
    """
    Apply two-layer PII scrubbing: regex first, then Guardrails.

    This provides defense-in-depth:
    1. Regex catches common patterns (fast, free)
    2. Guardrails catches sophisticated patterns (ML-based)

    Args:
        text: Input text that may contain PII
        guardrail_id: Bedrock Guardrail ID
        guardrail_version: Guardrail version
        source: "INPUT" for prompts, "OUTPUT" for responses

    Returns:
        Text with PII redacted
    """
    if not text or not isinstance(text, str):
        return text

    # Layer 1: Regex-based scrubbing (fast, free baseline)
    regex_scrubbed = scrub_pii_basic(text)

    # Layer 2: Guardrails ML-based detection
    result = apply_guardrail_filter(
        regex_scrubbed,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
        source=source,
    )

    if result["error"]:
        # Fail-safe: return regex-scrubbed text if Guardrails fails
        logger.warning(f"Guardrails failed, using regex-only: {result['error']}")
        return regex_scrubbed

    if result["pii_detected"]:
        pii_types = [p["type"] for p in result["pii_detected"]]
        logger.info(f"PII detected and anonymized: {pii_types}")

    return result["text"]


def scrub_text_guardrails_only(
    text: str,
    guardrail_id: str,
    guardrail_version: str,
    source: str = "OUTPUT",
) -> str:
    """
    Apply Guardrails-only PII scrubbing (no regex pre-filtering).

    Use this for isolated Guardrails testing without regex interference.

    Args:
        text: Input text that may contain PII
        guardrail_id: Bedrock Guardrail ID
        guardrail_version: Guardrail version
        source: "INPUT" for prompts, "OUTPUT" for responses

    Returns:
        Text with PII redacted by Guardrails only
    """
    if not text or not isinstance(text, str):
        return text

    # Guardrails ML-based detection only (no regex)
    result = apply_guardrail_filter(
        text,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
        source=source,
    )

    if result["error"]:
        logger.warning(f"Guardrails failed, returning original text: {result['error']}")
        return text

    if result["pii_detected"]:
        pii_types = [p["type"] for p in result["pii_detected"]]
        logger.info(f"PII detected and anonymized (Guardrails-only): {pii_types}")

    return result["text"]


# =============================================================================
# Regex-based PII Scrubbing (Fallback/Baseline)
# =============================================================================


def scrub_pii_basic(text: str) -> str:
    """
    Remove common PII patterns using regex (fast, free baseline).

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
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[EMAIL_REDACTED]",
        text,
    )

    # Phone: (555) 123-4567, 555-123-4567, 555.123.4567
    text = re.sub(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]", text)

    # Credit Card: 1234-5678-9012-3456, 1234 5678 9012 3456
    text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CC_REDACTED]", text)

    return text


# =============================================================================
# Record-level Scrubbing Functions
# =============================================================================


def scrub_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply regex-based PII scrubbing to all text fields in a log record.

    This is the fallback/baseline scrubber when Guardrails is not enabled.

    Scrubs (Bedrock Converse API format):
    - input.inputBodyJson.messages[].content[].text (user prompts)
    - input.inputBodyJson.system[].text (system prompts)
    - output.outputBodyJson.output.message.content[].text (model responses)

    Args:
        record: Bedrock invocation log record

    Returns:
        Record with PII redacted from text fields
    """
    # Scrub input messages (Converse API format)
    input_data = record.get("input", {})
    input_body = input_data.get("inputBodyJson", {})

    # Scrub user messages
    messages = input_body.get("messages", [])
    if isinstance(messages, list):
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for content_block in content:
                    if "text" in content_block:
                        content_block["text"] = scrub_pii_basic(content_block["text"])

    # Scrub system prompts
    system_data = input_body.get("system", [])
    if isinstance(system_data, list):
        for system_block in system_data:
            if "text" in system_block:
                system_block["text"] = scrub_pii_basic(system_block["text"])

    # Scrub output message content (Converse API format)
    output_data = record.get("output", {})
    output_body = output_data.get("outputBodyJson", {})
    output_obj = output_body.get("output", {})
    message = output_obj.get("message", {})

    content = message.get("content", [])
    if isinstance(content, list):
        for content_block in content:
            if "text" in content_block:
                content_block["text"] = scrub_pii_basic(content_block["text"])

    return record


def scrub_record_with_guardrails(
    record: Dict[str, Any],
    guardrail_id: str,
    guardrail_version: str,
) -> Dict[str, Any]:
    """
    Apply defense-in-depth PII scrubbing to a log record.

    Uses both regex and Guardrails ML-based detection for comprehensive coverage.

    Pipeline: Input → Regex Scrub → Guardrails API → Output

    NOTE: Uses source="OUTPUT" for all text fields because the ApplyGuardrail API
    only performs PII anonymization (replacing with tokens like {NAME}, {EMAIL})
    when source=OUTPUT. With source=INPUT, it only blocks content but doesn't
    anonymize - it returns the original text unchanged.

    Scrubs (Bedrock Converse API format):
    - input.inputBodyJson.messages[].content[].text (user prompts)
    - input.inputBodyJson.system[].text (system prompts)
    - output.outputBodyJson.output.message.content[].text (model responses)

    Args:
        record: Bedrock invocation log record
        guardrail_id: Bedrock Guardrail ID
        guardrail_version: Guardrail version

    Returns:
        Record with PII redacted from text fields
    """
    # NOTE: Use source="OUTPUT" for all fields to enable PII anonymization.
    # source="INPUT" only blocks content but doesn't anonymize.

    # Scrub input messages (Converse API format)
    input_data = record.get("input", {})
    input_body = input_data.get("inputBodyJson", {})

    # Scrub user messages
    messages = input_body.get("messages", [])
    if isinstance(messages, list):
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for content_block in content:
                    if "text" in content_block:
                        content_block["text"] = scrub_text_with_guardrails(
                            content_block["text"],
                            guardrail_id=guardrail_id,
                            guardrail_version=guardrail_version,
                            source="OUTPUT",  # Use OUTPUT for anonymization
                        )

    # Scrub system prompts
    system_data = input_body.get("system", [])
    if isinstance(system_data, list):
        for system_block in system_data:
            if "text" in system_block:
                system_block["text"] = scrub_text_with_guardrails(
                    system_block["text"],
                    guardrail_id=guardrail_id,
                    guardrail_version=guardrail_version,
                    source="OUTPUT",  # Use OUTPUT for anonymization
                )

    # Scrub output message content (Converse API format)
    output_data = record.get("output", {})
    output_body = output_data.get("outputBodyJson", {})
    output_obj = output_body.get("output", {})
    message = output_obj.get("message", {})

    content = message.get("content", [])
    if isinstance(content, list):
        for content_block in content:
            if "text" in content_block:
                content_block["text"] = scrub_text_with_guardrails(
                    content_block["text"],
                    guardrail_id=guardrail_id,
                    guardrail_version=guardrail_version,
                    source="OUTPUT",
                )

    return record


def scrub_record_guardrails_only(
    record: Dict[str, Any],
    guardrail_id: str,
    guardrail_version: str,
) -> Dict[str, Any]:
    """
    Apply Guardrails-only PII scrubbing to a log record (no regex).

    Use this for isolated Guardrails testing without regex interference.

    NOTE: Uses source="OUTPUT" for all text fields because the ApplyGuardrail API
    only performs PII anonymization (replacing with tokens like {NAME}, {EMAIL})
    when source=OUTPUT. With source=INPUT, it only blocks content but doesn't
    anonymize - it returns the original text unchanged.

    Scrubs (Bedrock Converse API format):
    - input.inputBodyJson.messages[].content[].text (user prompts)
    - input.inputBodyJson.system[].text (system prompts)
    - output.outputBodyJson.output.message.content[].text (model responses)

    Args:
        record: Bedrock invocation log record
        guardrail_id: Bedrock Guardrail ID
        guardrail_version: Guardrail version

    Returns:
        Record with PII redacted by Guardrails only
    """
    # NOTE: Use source="OUTPUT" for all fields to enable PII anonymization.
    # source="INPUT" only blocks content but doesn't anonymize.

    # Scrub input messages (Converse API format)
    input_data = record.get("input", {})
    input_body = input_data.get("inputBodyJson", {})

    # Scrub user messages
    messages = input_body.get("messages", [])
    if isinstance(messages, list):
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for content_block in content:
                    if "text" in content_block:
                        content_block["text"] = scrub_text_guardrails_only(
                            content_block["text"],
                            guardrail_id=guardrail_id,
                            guardrail_version=guardrail_version,
                            source="OUTPUT",  # Use OUTPUT for anonymization
                        )

    # Scrub system prompts
    system_data = input_body.get("system", [])
    if isinstance(system_data, list):
        for system_block in system_data:
            if "text" in system_block:
                system_block["text"] = scrub_text_guardrails_only(
                    system_block["text"],
                    guardrail_id=guardrail_id,
                    guardrail_version=guardrail_version,
                    source="OUTPUT",  # Use OUTPUT for anonymization
                )

    # Scrub output message content (Converse API format)
    output_data = record.get("output", {})
    output_body = output_data.get("outputBodyJson", {})
    output_obj = output_body.get("output", {})
    message = output_obj.get("message", {})

    content = message.get("content", [])
    if isinstance(content, list):
        for content_block in content:
            if "text" in content_block:
                content_block["text"] = scrub_text_guardrails_only(
                    content_block["text"],
                    guardrail_id=guardrail_id,
                    guardrail_version=guardrail_version,
                    source="OUTPUT",
                )

    return record
