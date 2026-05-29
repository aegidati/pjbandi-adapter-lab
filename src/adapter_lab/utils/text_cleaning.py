from __future__ import annotations

import re

from bs4 import BeautifulSoup

MONTHS = {
    "gennaio": "01",
    "febbraio": "02",
    "marzo": "03",
    "aprile": "04",
    "maggio": "05",
    "giugno": "06",
    "luglio": "07",
    "agosto": "08",
    "settembre": "09",
    "ottobre": "10",
    "novembre": "11",
    "dicembre": "12",
}


def clean_whitespace(text: str) -> str:
    """Normalize repeated whitespace into single spaces."""

    return re.sub(r"\s+", " ", text).strip()


def strip_html_tags(html: str) -> str:
    """Strip HTML tags and return visible text."""

    return clean_whitespace(BeautifulSoup(html, "lxml").get_text(" ", strip=True))


def normalize_italian_date(text: str) -> str | None:
    """Convert common Italian textual dates to ISO-like YYYY-MM-DD."""

    cleaned = clean_whitespace(text).lower()
    numeric_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", cleaned)
    if numeric_match:
        day, month, year = numeric_match.groups()
        year = year if len(year) == 4 else f"20{year}"
        return f"{year}-{int(month):02d}-{int(day):02d}"
    textual_match = re.search(
        r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        cleaned,
    )
    if textual_match:
        day, month_name, year = textual_match.groups()
        return f"{year}-{MONTHS[month_name]}-{int(day):02d}"
    return None


def truncate(text: str, max_len: int) -> str:
    """Truncate text to a maximum length with ellipsis if needed."""

    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"
