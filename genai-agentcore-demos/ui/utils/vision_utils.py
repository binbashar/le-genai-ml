"""Vision capability utilities for image upload and processing."""

import base64
import io
import logging
from typing import Optional

import streamlit as st
from PIL import Image

logger = logging.getLogger(__name__)

# Image processing configuration
MAX_IMAGE_SIZE = (1536, 1536)  # Max dimensions for Bedrock vision
JPEG_QUALITY = 95  # JPEG compression quality
WARNING_SIZE_KB = 3072  # Show warning for images larger than 3MB


def should_enable_vision(agent_type: str, agents_config: dict) -> bool:
    """Check if vision capability should be enabled for the given agent.

    Reads from agents_config YAML to determine if vision is enabled.
    Falls back to False if not configured.

    Args:
        agent_type: Agent identifier (e.g., "finance_personal_assistant")
        agents_config: Full agents configuration dict

    Returns:
        True if vision should be enabled for this agent, False otherwise
    """
    agent_info = agents_config.get("agents", {}).get(agent_type, {})
    capabilities = agent_info.get("capabilities", {})
    return capabilities.get("vision", False)


def process_image_to_base64(uploaded_file) -> Optional[str]:
    """Process uploaded image and encode to base64.

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        Base64-encoded image string or None if processing fails
    """
    try:
        logger.info(f"Processing uploaded image: {uploaded_file.name}")

        # Read image bytes
        image_bytes = uploaded_file.getvalue()

        # Open and process image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary
        if img.mode != "RGB":
            logger.debug(f"Converting image from {img.mode} to RGB")
            img = img.convert("RGB")

        # Resize to reasonable dimensions
        if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
            logger.debug(f"Resizing image from {img.size} to max {MAX_IMAGE_SIZE}")
            img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

        # Encode to base64 JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.info(f"Image processed: size={img.size}, encoded_size={len(image_base64)} bytes")
        return image_base64

    except Exception as e:
        logger.error(f"Failed to process image: {e}", exc_info=True)
        st.error(f"Failed to process image: {str(e)}")
        return None


def render_attached_image_in_chat(uploaded_file, width: int = 200):
    """Render attached image in chat message.

    Args:
        uploaded_file: Streamlit uploaded file object
        width: Image width in pixels
    """
    if uploaded_file:
        st.image(uploaded_file, width=width, caption="Attached image")
