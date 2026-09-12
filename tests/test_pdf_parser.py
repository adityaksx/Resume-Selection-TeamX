"""Tests for PDF text extraction."""

from __future__ import annotations

import os
import tempfile

import fitz  # PyMuPDF
import pytest

from app.parsers.pdf_parser import extract_text_from_pdf, PDFParsingError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_pdf(text: str, path: str) -> None:
    """Create a simple single-page PDF with the given text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractTextFromPDF:
    """Tests for extract_text_from_pdf()."""

    def test_extract_from_file_path(self, tmp_path):
        """Extract text from a valid PDF file path."""
        pdf_path = str(tmp_path / "test.pdf")
        _create_test_pdf("Hello World — PDF Parser Test", pdf_path)

        result = extract_text_from_pdf(pdf_path)

        assert "Hello World" in result
        assert "PDF Parser Test" in result

    def test_extract_from_bytes(self, tmp_path):
        """Extract text from raw PDF bytes."""
        pdf_path = str(tmp_path / "test.pdf")
        _create_test_pdf("Bytes extraction test content", pdf_path)

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        result = extract_text_from_pdf(pdf_bytes)
        assert "Bytes extraction test" in result

    def test_file_not_found(self):
        """Raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("/nonexistent/path/file.pdf")

    def test_non_pdf_extension(self, tmp_path):
        """Raise PDFParsingError for non-PDF file extensions."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not a PDF")

        with pytest.raises(PDFParsingError, match="Not a PDF file"):
            extract_text_from_pdf(str(txt_file))

    def test_invalid_bytes(self):
        """Raise PDFParsingError for corrupted/invalid PDF bytes."""
        with pytest.raises(PDFParsingError):
            extract_text_from_pdf(b"This is not a valid PDF content")

    def test_empty_pdf(self, tmp_path):
        """Raise PDFParsingError for a PDF with no text."""
        pdf_path = str(tmp_path / "empty.pdf")
        doc = fitz.open()
        doc.new_page()  # blank page, no text
        doc.save(pdf_path)
        doc.close()

        with pytest.raises(PDFParsingError, match="no extractable text"):
            extract_text_from_pdf(pdf_path)

    def test_multipage_pdf(self, tmp_path):
        """Extract text from a multi-page PDF."""
        pdf_path = str(tmp_path / "multi.pdf")
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1} content here", fontsize=12)
        doc.save(pdf_path)
        doc.close()

        result = extract_text_from_pdf(pdf_path)
        assert "Page 1" in result
        assert "Page 2" in result
        assert "Page 3" in result

    def test_text_is_cleaned(self, tmp_path):
        """Verify extracted text is cleaned (no excessive whitespace)."""
        pdf_path = str(tmp_path / "whitespace.pdf")
        _create_test_pdf("  Extra   spaces   here  ", pdf_path)

        result = extract_text_from_pdf(pdf_path)
        # Should not have runs of multiple spaces
        assert "   " not in result
