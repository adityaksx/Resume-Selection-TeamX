"""PDF text extraction using PyMuPDF (fitz)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF

from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)


class PDFParsingError(Exception):
    """Raised when a PDF cannot be parsed or contains no extractable text."""


def extract_text_from_pdf(source: Union[str, Path, bytes]) -> str:
    """Extract and clean text from a PDF file or byte buffer.

    Args:
        source: A file path (str or Path) or raw bytes of a PDF.

    Returns:
        Cleaned text content of the PDF.

    Raises:
        PDFParsingError: If the PDF is invalid, empty, or contains no text.
        FileNotFoundError: If a file path is provided but does not exist.
    """
    try:
        if isinstance(source, bytes):
            doc = fitz.open(stream=source, filetype="pdf")
        else:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"PDF file not found: {path}")
            if not path.suffix.lower() == ".pdf":
                raise PDFParsingError(f"Not a PDF file: {path}")
            doc = fitz.open(str(path))
    except fitz.FileDataError as exc:
        raise PDFParsingError(f"Invalid or corrupted PDF: {exc}") from exc
    except Exception as exc:
        if isinstance(exc, (FileNotFoundError, PDFParsingError)):
            raise
        raise PDFParsingError(f"Failed to open PDF: {exc}") from exc

    try:
        pages_text: list[str] = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text and text.strip():
                pages_text.append(text)

        if not pages_text:
            raise PDFParsingError(
                "PDF contains no extractable text. "
                "It may be a scanned document or image-based PDF."
            )

        raw_text = "\n".join(pages_text)
        cleaned = clean_text(raw_text)

        if not cleaned:
            raise PDFParsingError("PDF text was empty after cleaning.")

        logger.info(
            "Extracted %d characters from %d page(s).",
            len(cleaned),
            len(pages_text),
        )
        return cleaned

    finally:
        doc.close()


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """Extract text from a Streamlit UploadedFile object.

    Args:
        uploaded_file: A Streamlit UploadedFile (has .read() and .name).

    Returns:
        Cleaned text content.

    Raises:
        PDFParsingError: If extraction fails.
    """
    raw_bytes = uploaded_file.read()
    if not raw_bytes:
        raise PDFParsingError(f"Uploaded file '{uploaded_file.name}' is empty.")
    return extract_text_from_pdf(raw_bytes)
