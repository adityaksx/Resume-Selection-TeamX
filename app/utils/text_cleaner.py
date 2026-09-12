"""Text cleaning utilities for extracted PDF content."""

import re
import unicodedata


def clean_text(text: str) -> str:
    """Clean raw text extracted from a PDF.

    Steps:
        1. Normalize unicode characters (NFKD → recompose).
        2. Remove non-printable control characters (keep newlines/tabs).
        3. Collapse multiple whitespace on the same line.
        4. Collapse multiple blank lines into one.
        5. Strip leading/trailing whitespace.

    Args:
        text: Raw text from PDF extraction.

    Returns:
        Cleaned text string.
    """
    if not text:
        return ""

    # Normalize unicode (e.g. ligatures like ﬁ → fi)
    text = unicodedata.normalize("NFKD", text)
    text = unicodedata.normalize("NFC", text)

    # Remove control characters but keep newlines and tabs
    text = re.sub(r"[^\S\n\t]+", " ", text)  # non-newline whitespace → single space
    text = re.sub(r"[^\x20-\x7E\n\t\u00A0-\uFFFF]", "", text)  # remove control chars

    # Collapse multiple blank lines into a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip each line
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()


def truncate_text(text: str, max_chars: int = 5000) -> str:
    """Truncate text to a maximum character count with an ellipsis marker.

    Args:
        text: Input text.
        max_chars: Maximum character length.

    Returns:
        Truncated text.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated]"
