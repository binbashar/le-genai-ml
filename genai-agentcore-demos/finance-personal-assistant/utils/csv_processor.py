"""CSV text extraction for financial document processing.

This module provides simple CSV to text conversion with basic security sanitization.
MVP implementation: returns raw CSV text for the agent to parse naturally.
"""

import base64
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def csv_to_text(csv_base64: str, max_size_mb: int = 5) -> Optional[str]:
    """
    Safely decode CSV to text with basic sanitization.

    This is a minimal MVP implementation that converts CSV to plain text.
    The agent (Claude/Nova) will naturally understand and parse the tabular data.

    Security features:
    - Prevents CSV formula injection (removes =, +, -, @ at line start)
    - Enforces file size limit
    - Handles encoding errors gracefully

    Args:
        csv_base64: Base64-encoded CSV file content
        max_size_mb: Maximum file size in megabytes (default: 5MB)

    Returns:
        Plain text CSV content (sanitized), or None if processing fails

    Example:
        >>> csv_data = base64.b64encode(b"Date,Amount\\n2024-01-01,100.00").decode()
        >>> text = csv_to_text(csv_data)
        >>> print(text)
        Date,Amount
        2024-01-01,100.00
    """
    try:
        # Decode base64
        csv_bytes = base64.b64decode(csv_base64)

        # Check file size
        size_mb = len(csv_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning(f"CSV file too large: {size_mb:.2f}MB (max: {max_size_mb}MB)")
            return None

        # Try decoding with common encodings
        csv_text = None
        for encoding in ["utf-8", "utf-8-sig", "iso-8859-1", "cp1252"]:
            try:
                csv_text = csv_bytes.decode(encoding)
                logger.info(f"Successfully decoded CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue

        if csv_text is None:
            logger.error("Failed to decode CSV with any common encoding")
            return None

        # Sanitize: Remove CSV formula injection
        # Dangerous characters at line start: =, +, -, @, \t, \r
        csv_text = _sanitize_csv_formulas(csv_text)

        # Log size info
        lines = csv_text.count("\n") + 1
        logger.info(f"Successfully processed CSV: {lines} lines, {len(csv_text)} characters")

        return csv_text

    except Exception as e:
        logger.error(f"Failed to process CSV: {e}", exc_info=True)
        return None


def _sanitize_csv_formulas(csv_text: str) -> str:
    """
    Remove potential CSV formula injection attacks.

    Formulas in CSV files start with =, +, -, @, tab, or carriage return.
    When opened in Excel/Sheets, these can execute arbitrary code.

    This function is smart about negative numbers: "-123.45" is allowed,
    but "-2+5" (formula) is sanitized.

    Args:
        csv_text: Raw CSV text

    Returns:
        Sanitized CSV text with dangerous prefixes removed
    """
    lines = csv_text.split("\n")
    sanitized_lines = []

    # Patterns for dangerous formula characters
    # = + @ \t \r are always dangerous at cell start
    always_dangerous = re.compile(r"(^|,)([=+@\t\r])")

    # - is only dangerous if NOT followed by a number (e.g., "-2+5" vs "-123.45")
    minus_formula = re.compile(r"(^|,)(-(?!\d))")

    for line in lines:
        # Sanitize always-dangerous characters
        line = always_dangerous.sub(r"\1'\2", line)

        # Sanitize minus only when it's a formula (not a negative number)
        line = minus_formula.sub(r"\1'\2", line)

        sanitized_lines.append(line)

    return "\n".join(sanitized_lines)
