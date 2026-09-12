"""Document parsing package supporting PDF, DOCX, and TXT formats."""

from app.parsers.document_parser import (
    DocumentParsingError,
    extract_text_from_document,
    extract_text_from_docx,
    extract_text_from_txt,
    extract_text_from_uploaded_document,
)
from app.parsers.pdf_parser import PDFParsingError, extract_text_from_pdf, extract_text_from_uploaded_file

__all__ = [
    "extract_text_from_pdf",
    "extract_text_from_docx",
    "extract_text_from_txt",
    "extract_text_from_document",
    "extract_text_from_uploaded_document",
    "extract_text_from_uploaded_file",
    "DocumentParsingError",
    "PDFParsingError",
]
