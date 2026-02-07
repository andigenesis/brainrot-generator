"""Input processing: extract text from uploaded files."""
from io import BytesIO
from typing import Optional

from pypdf import PdfReader


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from uploaded file.

    Supported formats:
        - PDF (.pdf)
        - Plain text (.txt)

    Args:
        file_bytes: File content as bytes
        filename: Original filename (used to determine file type)

    Returns:
        Extracted text content

    Raises:
        ValueError: If file format is not supported
    """
    filename_lower = filename.lower()

    # PDF files
    if filename_lower.endswith('.pdf'):
        return _extract_pdf_text(file_bytes)

    # Plain text files
    elif filename_lower.endswith('.txt'):
        return _extract_plain_text(file_bytes)

    else:
        raise ValueError(
            f"Unsupported file format: {filename}. "
            "Supported formats: .pdf, .txt"
        )


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF file."""
    pdf_file = BytesIO(file_bytes)
    reader = PdfReader(pdf_file)

    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    if not text_parts:
        raise ValueError("No text content found in PDF")

    return "\n".join(text_parts)


def _extract_plain_text(file_bytes: bytes) -> str:
    """Extract text from plain text file."""
    # Try UTF-8 first, fall back to latin-1
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1')
