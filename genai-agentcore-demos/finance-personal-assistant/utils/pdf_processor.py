"""PDF to image conversion for financial document processing.

This module provides simple PDF to image conversion using PyMuPDF (fitz).
MVP implementation: converts only the first page of a PDF to an image.
"""

import base64
import io
import logging
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def pdf_first_page_to_image(pdf_base64: str) -> Optional[str]:
    """
    Convert the first page of a PDF to a base64-encoded JPEG image.

    This is a minimal MVP implementation that processes only the first page.
    Multi-page support can be added later if needed.

    Args:
        pdf_base64: Base64-encoded PDF file content

    Returns:
        Base64-encoded JPEG image of the first page, or None if conversion fails

    Example:
        >>> pdf_data = base64.b64encode(open("invoice.pdf", "rb").read()).decode()
        >>> image_base64 = pdf_first_page_to_image(pdf_data)
        >>> # Now pass image_base64 to vision_analyzer.analyze_image()
    """
    try:
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(pdf_base64)

        # Open PDF with PyMuPDF
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

        if pdf_document.page_count == 0:
            logger.warning("PDF has no pages")
            return None

        # Get first page
        page = pdf_document[0]

        # Render page to image (pixmap)
        # zoom=2.0 gives 144 DPI (good quality for OCR)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to JPEG bytes
        img_bytes = pix.tobytes("jpeg")

        # Close PDF
        pdf_document.close()

        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        logger.info(f"Successfully converted PDF first page to image ({len(img_base64)} bytes)")
        return img_base64

    except Exception as e:
        logger.error(f"Failed to convert PDF to image: {e}", exc_info=True)
        return None
