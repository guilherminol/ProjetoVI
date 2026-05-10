"""
PDF text extraction with dual-parser strategy:
  Primary:  pymupdf4llm  — for digital/born-digital PDFs
  Fallback: Docling      — for scanned/legacy/image-based PDFs

Fallback trigger: pymupdf4llm output < 200 characters (empty or image-based doc).
"""
import logging
from pathlib import Path

import pymupdf4llm

logger = logging.getLogger(__name__)

_MIN_DIGITAL_CHARS = 200


def _extract_with_pymupdf(file_path: str) -> str:
    return pymupdf4llm.to_markdown(file_path)


def _extract_with_docling(file_path: str) -> str:
    from docling.document_converter import DocumentConverter  # lazy import — heavy startup
    converter = DocumentConverter()
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


def parse_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using the dual-parser strategy.

    Raises:
        ValueError: If file does not exist or is not a PDF.
        RuntimeError: If both parsers fail to extract any text.
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"PDF file not found: {file_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    logger.info("Parsing PDF with pymupdf4llm: %s", path.name)
    text = _extract_with_pymupdf(file_path)

    if len(text.strip()) < _MIN_DIGITAL_CHARS:
        logger.warning(
            "pymupdf4llm returned %d chars (< %d threshold) for %s — "
            "switching to Docling OCR fallback",
            len(text.strip()),
            _MIN_DIGITAL_CHARS,
            path.name,
        )
        text = _extract_with_docling(file_path)

    if not text.strip():
        raise RuntimeError(
            f"Both parsers failed to extract text from {path.name}. "
            "File may be encrypted, corrupted, or purely graphical."
        )

    logger.info("Extracted %d characters from %s", len(text), path.name)
    return text
