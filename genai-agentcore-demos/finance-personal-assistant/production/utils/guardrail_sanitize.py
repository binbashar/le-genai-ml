"""Guardrail pre-check utility for validating user input.

This module provides a utility to validate user input using the AWS Bedrock
ApplyGuardrail API BEFORE agent processing. This prevents blocked content from
entering the system and contaminating conversation history.

References:
- AWS ApplyGuardrail API: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html
"""

import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def apply_guardrail_text(
    text: str,
    *,
    guardrail_id: Optional[str] = None,
    guardrail_arn: Optional[str] = None,
    guardrail_version: str = "1",
    source: str = "INPUT",
    region_name: str = "us-west-2",
) -> Dict[str, Any]:
    """
    Apply guardrail to text without model invocation.

    Uses the AWS Bedrock ApplyGuardrail API to evaluate text against
    guardrail policies (content filters, denied topics, PII, word blocks).

    Args:
        text: Text to evaluate
        guardrail_id: Guardrail ID (mutually exclusive with guardrail_arn)
        guardrail_arn: Guardrail ARN (mutually exclusive with guardrail_id)
        guardrail_version: Guardrail version or "DRAFT" (default: "1")
        source: "INPUT" for user content, "OUTPUT" for model responses (default: "INPUT")
        region_name: AWS region (default: "us-west-2")

    Returns:
        Dict with:
        - action: "NONE" | "GUARDRAIL_INTERVENED"
        - sanitized_text: Original text (if safe) or blocked message
        - is_safe: True if no intervention occurred
        - action_reason: Explanation if blocked (optional)

    Raises:
        ValueError: If neither guardrail_id nor guardrail_arn is provided
    """
    if not text:
        return {
            "action": "NONE",
            "sanitized_text": text,
            "is_safe": True,
        }

    # Validate guardrail identifier
    if not guardrail_id and not guardrail_arn:
        raise ValueError("Either guardrail_id or guardrail_arn must be provided")

    guardrail_identifier = guardrail_arn or guardrail_id

    # Initialize Bedrock Runtime client
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=region_name)

    try:
        # Call ApplyGuardrail API
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=guardrail_identifier,
            guardrailVersion=guardrail_version,
            source=source,
            content=[{"text": {"text": text}}],
        )

        action = response.get("action", "NONE")
        is_safe = action == "NONE"

        # Extract sanitized text
        if is_safe:
            # When action=NONE, outputs array is empty - use original text
            sanitized_text = text
        else:
            # When action=GUARDRAIL_INTERVENED, outputs contains blocked/masked text
            outputs = response.get("outputs", [])
            if outputs and "text" in outputs[0]:
                sanitized_text = outputs[0]["text"]
            else:
                # Fallback: empty string if no output provided
                sanitized_text = ""

        result = {
            "action": action,
            "sanitized_text": sanitized_text,
            "is_safe": is_safe,
        }

        # Add action reason if intervention occurred
        if not is_safe:
            action_reason = response.get("actionReason", "Unknown")
            result["action_reason"] = action_reason
            logger.warning(
                f"[GUARDRAIL] Text blocked by ApplyGuardrail API: {action_reason}"
            )

        return result

    except ClientError as e:
        # Log error but fail-safe to allow content (avoid blocking legitimate queries)
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(
            f"[GUARDRAIL] API error ({error_code}): {error_message}. "
            f"Failing safe - allowing content."
        )

        # Fail-safe: treat as safe to avoid blocking legitimate content on API errors
        return {
            "action": "ERROR",
            "sanitized_text": text,
            "is_safe": True,
            "error": error_message,
        }

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            f"[GUARDRAIL] Unexpected error in apply_guardrail_text: {e}. "
            f"Failing safe - allowing content.",
            exc_info=True,
        )

        return {
            "action": "ERROR",
            "sanitized_text": text,
            "is_safe": True,
            "error": str(e),
        }
