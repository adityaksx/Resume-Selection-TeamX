"""Unified document text extraction supporting PDF, DOCX, and TXT (plan.md Phase 7A).

Extracts and cleans plain text from documents regardless of format,
allowing mixed batches of candidate resumes and flexible job descriptions.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Union

import docx
import fitz  # PyMuPDF

from app.parsers.pdf_parser import PDFParsingError, extract_text_from_pdf
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)


class DocumentParsingError(Exception):
    """Raised when a document cannot be parsed or contains no extractable text."""


def extract_text_from_docx(source: Union[str, Path, bytes]) -> str:
    """Extract and clean text from a DOCX file or byte buffer.

    Args:
        source: File path (str or Path) or raw bytes of a DOCX document.

    Returns:
        Cleaned text content.

    Raises:
        DocumentParsingError: If file is malformed, empty, or unreadable.
        FileNotFoundError: If a file path is provided but does not exist.
    """
    try:
        if isinstance(source, bytes):
            if not source or len(source.strip()) == 0:
                raise DocumentParsingError("DOCX file is empty.")
            doc_stream = io.BytesIO(source)
            doc = docx.Document(doc_stream)
        else:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"DOCX file not found: {path}")
            if path.stat().st_size == 0:
                raise DocumentParsingError(f"DOCX file is empty: {path}")
            doc = docx.Document(str(path))
    except (FileNotFoundError, DocumentParsingError):
        raise
    except Exception as exc:
        raise DocumentParsingError(f"Invalid or corrupted DOCX file: {exc}") from exc

    try:
        parts: list[str] = []

        # Extract text from standard paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                parts.append(text)

        # Extract text from tables if present
        for table in doc.tables:
            for row in table.rows:
                row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_texts:
                    parts.append(" | ".join(row_texts))

        if not parts:
            raise DocumentParsingError("DOCX file contains no extractable text.")

        raw_text = "\n".join(parts)
        cleaned = clean_text(raw_text)

        if not cleaned:
            raise DocumentParsingError("DOCX text was empty after cleaning.")

        logger.info("Extracted %d characters from DOCX.", len(cleaned))
        return cleaned

    except DocumentParsingError:
        raise
    except Exception as exc:
        raise DocumentParsingError(f"Failed to extract text from DOCX: {exc}") from exc


def extract_text_from_txt(source: Union[str, Path, bytes]) -> str:
    """Extract and clean text from a TXT file or byte buffer.

    Handles UTF-8, UTF-8-SIG, and Latin-1 fallback encodings gracefully.

    Args:
        source: File path (str or Path) or raw bytes of a text document.

    Returns:
        Cleaned text content.

    Raises:
        DocumentParsingError: If file is empty or cannot be decoded.
        FileNotFoundError: If a file path is provided but does not exist.
    """
    raw_bytes: bytes

    if isinstance(source, bytes):
        raw_bytes = source
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"TXT file not found: {path}")
        raw_bytes = path.read_bytes()

    if not raw_bytes or len(raw_bytes.strip()) == 0:
        raise DocumentParsingError("Text file is empty.")

    # Try standard encodings in order
    decoded_text: str | None = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            decoded_text = raw_bytes.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if decoded_text is None:
        raise DocumentParsingError("Failed to decode text file with supported encodings.")

    cleaned = clean_text(decoded_text)
    if not cleaned:
        raise DocumentParsingError("Text file was empty after cleaning.")

    logger.info("Extracted %d characters from TXT.", len(cleaned))
    return cleaned


def extract_text_from_document(
    source: Union[str, Path, bytes],
    filename: str | None = None,
) -> str:
    """Extract plain text from a document (PDF, DOCX, or TXT).

    Dispatches to format-specific parser based on filename extension or file path.

    Args:
        source: File path or raw bytes.
        filename: Optional filename used to determine format when source is bytes.

    Returns:
        Cleaned plain text.

    Raises:
        DocumentParsingError: If format is unsupported or parsing fails.
    """
    # Determine extension
    ext = ""
    if filename:
        ext = Path(filename).suffix.lower()
    elif isinstance(source, (str, Path)):
        ext = Path(source).suffix.lower()

    try:
        if ext == ".pdf":
            return extract_text_from_pdf(source)
        elif ext == ".docx":
            return extract_text_from_docx(source)
        elif ext in (".txt", ".text", ".md"):
            return extract_text_from_txt(source)
        elif not ext:
            # Try guessing from raw bytes magic headers if extension missing
            if isinstance(source, bytes) and source.startswith(b"%PDF"):
                return extract_text_from_pdf(source)
            if isinstance(source, bytes) and source.startswith(b"PK\x03\x04"):
                return extract_text_from_docx(source)
            # Default to text
            return extract_text_from_txt(source)
        else:
            raise DocumentParsingError(
                f"Unsupported document format '{ext}'. Supported formats: .pdf, .docx, .txt"
            )
    except PDFParsingError as exc:
        raise DocumentParsingError(str(exc)) from exc


def extract_text_from_uploaded_document(uploaded_file) -> str:
    """Extract text from a Streamlit UploadedFile object (.pdf, .docx, or .txt).

    Args:
        uploaded_file: Streamlit UploadedFile with .read() and .name.

    Returns:
        Cleaned text string.

    Raises:
        DocumentParsingError: If file is empty or extraction fails.
    """
    raw_bytes = uploaded_file.read()
    if not raw_bytes:
        raise DocumentParsingError(f"Uploaded file '{uploaded_file.name}' is empty.")
    return extract_text_from_document(raw_bytes, filename=uploaded_file.name)
