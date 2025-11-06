"""
Vision context injection utilities for financial agents.

Provides patterns for processing vision analysis results
and injecting them into user messages for agent context.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VisionContextFormatter:
    """
    Format vision data for context injection.

    Formatter with static methods for stateless operation.
    """

    @staticmethod
    def format_data(data: dict[str, Any]) -> str:
        """
        Format vision-extracted data for context injection.

        Args:
            data: Dictionary of extracted financial data

        Returns:
            Formatted string with structured data for injection into user message

        Example:
            >>> data = {"merchant": "Starbucks", "total": 5.50, "items": ["Coffee"]}
            >>> formatted = VisionContextFormatter.format_data(data)
            >>> print(formatted)
            Merchant: Starbucks
            Total: $5.50
            Items: 1 items
              - Coffee
        """
        if not data:
            return ""

        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                # Format list items (e.g., line items from receipt)
                if value:
                    lines.append(f"{key.title()}: {len(value)} items")
                    for item in value[:3]:  # Show first 3 items
                        lines.append(f"  - {item}")
                    if len(value) > 3:
                        lines.append(f"  - ... and {len(value) - 3} more")
                else:
                    lines.append(f"{key.title()}: (empty)")
            elif isinstance(value, (int, float)):
                # Format numbers (e.g., totals, prices)
                if key.lower() in ["total", "subtotal", "tax", "amount"]:
                    lines.append(f"{key.title()}: ${value:.2f}")
                else:
                    lines.append(f"{key.title()}: {value}")
            else:
                # Format strings (e.g., merchant, date, category)
                lines.append(f"{key.title()}: {value}")

        return "\n".join(lines)


def inject_vision_context(
    user_message: str,
    vision_result: Optional[dict[str, Any]],
) -> str:
    """
    Inject vision analysis context into user message.

    Factory function following pattern for context injection.
    Handles all vision status cases (success, unknown, error).

    Args:
        user_message: Original user prompt
        vision_result: Vision analysis result from analyze_image()

    Returns:
        User message with vision context injected

    Example:
        >>> from utils.vision_analyzer import analyze_image
        >>> vision_result = analyze_image(image_base64="...")
        >>> enhanced_message = inject_vision_context("Track this expense", vision_result)
        >>> # enhanced_message now contains vision context + original message
    """
    if not vision_result:
        return user_message

    status = vision_result["status"]

    if status == "unknown":
        # Image not recognized as financial document
        return f"""[Vision Analysis: Image not recognized as financial document]

{user_message}"""

    elif status == "success":
        # Financial document detected - inject structured data
        formatter = VisionContextFormatter()
        data_summary = formatter.format_data(vision_result["data"])
        keywords_str = ", ".join(vision_result["keywords"])

        return f"""[Vision Analysis: {vision_result["summary"]}
Keywords: {keywords_str}
{data_summary}]

{user_message}"""

    elif status == "error":
        # Vision API error - inject error context
        return f"""[Vision Analysis: Failed - {vision_result["summary"]}]

{user_message}"""

    # Fallback: unknown status
    return user_message
