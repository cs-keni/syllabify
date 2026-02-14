"""
Extract plain text from PDF, DOCX, or TXT files for syllabus parsing.
"""
import io
from pathlib import Path


def extract_text_from_file(file) -> str:
    """
    Extract plain text from a file (PDF, DOCX, or TXT).
    file: file-like object (e.g. from request.files) or bytes, must have .filename or detect by content.
    Returns plaintext string for parsing.
    """
    # Get filename and content
    filename = getattr(file, "filename", None) or ""
    if hasattr(file, "read"):
        content = file.read()
        file.seek(0)  # Reset for possible reuse
    else:
        content = file

    ext = (Path(filename).suffix or "").lower()
    if ext == ".txt":
        return _extract_txt(content)
    if ext == ".pdf":
        return _extract_pdf(content)
    if ext in (".docx", ".doc"):
        return _extract_docx(content)

    # Fallback: try to detect by magic bytes
    if content[:4] == b"%PDF":
        return _extract_pdf(content)
    # DOCX is a ZIP file
    if content[:2] == b"PK":
        return _extract_docx(content)

    # Default: treat as UTF-8 text
    return _extract_txt(content)


def _extract_txt(content: bytes) -> str:
    """Extract text from plaintext file."""
    return content.decode("utf-8", errors="replace")


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    import pdfplumber

    parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n\n".join(parts) if parts else ""


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(content))
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                parts.append(row_text)
    return "\n\n".join(parts) if parts else ""
