from __future__ import annotations

import re

from adapter_lab.utils.text_cleaning import clean_whitespace, normalize_italian_date
from adapter_lab.utils.urls import normalize_url

TITLE_PATTERNS = [
    re.compile(r"(?:bando|avviso|misura)[:\s]+(.+)", re.IGNORECASE),
]
DATE_PATTERNS = [
    re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
    re.compile(
        r"(\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4})",
        re.IGNORECASE,
    ),
]
DEADLINE_PATTERNS = [
    re.compile(
        r"(?:scadenza|termine(?:\s+per\s+la\s+presentazione)?)[^\d]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:scadenza|termine(?:\s+per\s+la\s+presentazione)?)[^\d]*(\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4})",
        re.IGNORECASE,
    ),
]
URL_PATTERN = re.compile(r"https?://[^\s)>,]+", re.IGNORECASE)
EURO_PATTERN = re.compile(r"€\s?[\d\.,]+|[\d\.,]+\s?euro", re.IGNORECASE)


class DeterministicExtractor:
    """Regex-based extractor for common Italian funding terminology."""

    def extract_title(self, text: str) -> str | None:
        """Extract a likely title from free text."""

        cleaned = clean_whitespace(text)
        for pattern in TITLE_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                return clean_whitespace(match.group(1))
        first_sentence = cleaned.split(".")
        return first_sentence[0][:200] if cleaned else None

    def extract_publication_date(self, text: str) -> str | None:
        """Extract a likely publication date from text."""

        for pattern in DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                return normalize_italian_date(match.group(1))
        return None

    def extract_deadline(self, text: str) -> str | None:
        """Extract an application deadline from text."""

        for pattern in DEADLINE_PATTERNS:
            match = pattern.search(text)
            if match:
                return normalize_italian_date(match.group(1))
        return None

    def extract_attachment_urls(self, text: str, base_url: str) -> list[str]:
        """Extract attachment URLs found in text."""

        urls = [normalize_url(match.group(0), base_url) for match in URL_PATTERN.finditer(text)]
        seen: set[str] = set()
        ordered: list[str] = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                ordered.append(url)
        return ordered

    def extract_euro_amounts(self, text: str) -> list[str]:
        """Extract euro-denominated budget amounts from text."""

        return [clean_whitespace(match.group(0)) for match in EURO_PATTERN.finditer(text)]
