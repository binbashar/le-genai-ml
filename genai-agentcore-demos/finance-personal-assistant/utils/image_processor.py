"""Image processing utilities for vision analysis.

This module provides simple, focused image processing functionality:
- Resize images to appropriate dimensions for Bedrock API
- Optimize file size while maintaining quality
- Convert to base64 encoding

Follows SOLID principles:
- Single Responsibility: Only handles image processing
- Reusable across different agents (DRY)
"""

import io
import base64
import logging
from typing import Tuple

from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

# Default maximum dimensions (can be overridden)
DEFAULT_MAX_SIZE = (1536, 1536)  # Conservative size for API payload limits


def process_image(
    image_bytes: bytes,
    max_size: Tuple[int, int] = DEFAULT_MAX_SIZE
) -> str:
    """
    Process and encode image for Bedrock vision API.

    This function:
    1. Opens the image from bytes
    2. Converts to RGB format (required by JPEG)
    3. Resizes to fit within max_size (preserves aspect ratio)
    4. Enhances contrast for better OCR recognition
    5. Encodes to base64 JPEG string

    Args:
        image_bytes: Raw image bytes (any PIL-supported format)
        max_size: Maximum dimensions as (width, height) tuple
                 Images larger than this will be resized

    Returns:
        Base64-encoded JPEG string ready for API submission

    Raises:
        PIL.UnidentifiedImageError: If image format is not recognized
        ValueError: If image_bytes is empty or invalid

    Examples:
        >>> with open("receipt.jpg", "rb") as f:
        ...     encoded = process_image(f.read())
        >>> len(encoded)  # Should be reasonable size
        245678
    """
    if not image_bytes:
        raise ValueError("image_bytes cannot be empty")

    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        original_size = image.size
        logger.debug(f"Original image size: {original_size}, format: {image.format}")

        # Convert to RGB if necessary (required for JPEG encoding)
        if image.mode != "RGB":
            logger.debug(f"Converting image from {image.mode} to RGB")
            image = image.convert("RGB")

        # Resize if needed (preserves aspect ratio via thumbnail)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            logger.debug(f"Resizing image from {image.size} to max {max_size}")
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            logger.debug(f"Resized to: {image.size}")

        # Enhance contrast for better OCR/text recognition
        # This helps vision models read text on receipts more accurately
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)  # Subtle enhancement (10% increase)

        # Encode to base64 JPEG
        buffer = io.BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=95,  # High quality, good balance with file size
            optimize=True  # Optimize compression
        )

        base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Log size information for monitoring
        encoded_size_kb = len(base64_string) / 1024
        logger.info(
            f"Image processed: {original_size} -> {image.size}, "
            f"encoded size: {encoded_size_kb:.1f}KB"
        )

        return base64_string

    except Exception as e:
        logger.error(f"Failed to process image: {e}", exc_info=True)
        raise


def estimate_encoded_size(image_bytes: bytes) -> int:
    """
    Estimate base64-encoded size without full processing.

    Useful for quick validation before expensive processing.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Estimated encoded size in bytes

    Note:
        Base64 encoding increases size by ~33% (4/3 ratio)
    """
    return len(image_bytes) * 4 // 3


def validate_image_size(image_bytes: bytes, max_size_mb: float = 10.0) -> bool:
    """
    Validate that image is within acceptable size limits.

    Args:
        image_bytes: Raw image bytes
        max_size_mb: Maximum allowed size in megabytes

    Returns:
        True if image is within limits, False otherwise
    """
    size_mb = len(image_bytes) / (1024 * 1024)

    if size_mb > max_size_mb:
        logger.warning(
            f"Image size {size_mb:.2f}MB exceeds limit of {max_size_mb}MB"
        )
        return False

    return True
