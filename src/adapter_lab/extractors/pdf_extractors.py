from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from adapter_lab.utils.text_cleaning import clean_whitespace


class PdfExtractor:
    """PDF extraction helpers using pypdf."""

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""

        reader = PdfReader(BytesIO(pdf_bytes))
        texts = [page.extract_text() or "" for page in reader.pages]
        return clean_whitespace(" ".join(texts))

    def extract_text_from_file(self, path: str | Path) -> str:
        """Extract text from a PDF file path."""

        return self.extract_text(Path(path).read_bytes())
