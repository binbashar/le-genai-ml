"""Document upload utilities for multi-format file support (images, PDFs, CSVs)."""

import base64
import logging
from typing import Optional, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

# File size limits
MAX_FILE_SIZE_MB = 10  # Maximum file size for uploads


def should_enable_documents(agent_type: str, agents_config: dict) -> bool:
    """Check if document upload capability should be enabled for the given agent.

    Reads from agents_config YAML to determine if documents (PDF/CSV) are enabled.
    Falls back to False if not configured.

    Args:
        agent_type: Agent identifier (e.g., "finance_personal_assistant")
        agents_config: Full agents configuration dict

    Returns:
        True if documents should be enabled for this agent, False otherwise
    """
    agent_info = agents_config.get("agents", {}).get(agent_type, {})
    capabilities = agent_info.get("capabilities", {})
    return capabilities.get("documents", False)


def get_file_type_from_name(filename: str) -> str:
    """Extract file type from filename.

    Args:
        filename: Name of the uploaded file

    Returns:
        File type string: "image", "pdf", "csv", or "unknown"
    """
    ext = filename.lower().split(".")[-1]

    if ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        return "image"
    elif ext == "pdf":
        return "pdf"
    elif ext == "csv":
        return "csv"
    else:
        return "unknown"


def process_document_to_base64(uploaded_file) -> Optional[Tuple[str, str]]:
    """Process uploaded document and encode to base64.

    Supports images, PDFs, and CSVs. Returns base64 string and filename.

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        Tuple of (base64_string, filename) or None if processing fails
    """
    try:
        filename = uploaded_file.name
        logger.info(f"Processing uploaded document: {filename}")

        # Check file size
        file_bytes = uploaded_file.getvalue()
        size_mb = len(file_bytes) / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            st.error(f"File too large: {size_mb:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)")
            logger.warning(f"File {filename} exceeds size limit: {size_mb:.1f}MB")
            return None

        # Encode to base64
        doc_base64 = base64.b64encode(file_bytes).decode("utf-8")

        logger.info(
            f"Document processed: filename={filename}, size={size_mb:.2f}MB, encoded_size={len(doc_base64)} bytes"
        )
        return doc_base64, filename

    except Exception as e:
        logger.error(f"Failed to process document: {e}", exc_info=True)
        st.error(f"Failed to process document: {str(e)}")
        return None


def render_attached_document_in_chat(uploaded_file, file_type: str):
    """Render attached document indicator in chat message.

    Args:
        uploaded_file: Streamlit uploaded file object
        file_type: Type of file ("image", "pdf", "csv", "unknown")
    """
    if not uploaded_file:
        return

    size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)

    # Show image preview for images
    if file_type == "image":
        st.image(uploaded_file, width=200, caption="Attached image")
    else:
        # Show file info for non-image documents
        icon = {"pdf": "📄", "csv": "📊"}.get(file_type, "📎")
        st.caption(f"{icon} **{uploaded_file.name}** ({size_mb:.2f} MB)")
