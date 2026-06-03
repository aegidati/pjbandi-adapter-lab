from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from adapter_lab.utils.text_cleaning import clean_whitespace

logger = logging.getLogger(__name__)


class PdfExtractor:
    """PDF extraction helpers using pypdf."""

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes in a best-effort way."""

        try:
            reader = PdfReader(BytesIO(pdf_bytes))
        except Exception as exc:
            logger.warning("PDF reader initialization failed: %s", exc)
            return ""

        try:
            page_count = len(reader.pages)
        except Exception as exc:
            logger.warning("PDF page index resolution failed: %s", exc)
            return ""

        texts: list[str] = []
        for idx in range(page_count):
            try:
                page = reader.pages[idx]
                texts.append(page.extract_text() or "")
            except Exception as exc:
                logger.warning("PDF page extraction failed at page %s: %s", idx, exc)
                continue

        return clean_whitespace(" ".join(texts))

    def extract_text_from_file(self, path: str | Path) -> str:
        """Extract text from a PDF file path."""

        return self.extract_text(Path(path).read_bytes())
