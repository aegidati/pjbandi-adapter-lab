from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse


def normalize_url(url: str, base_url: str) -> str:
    """Return an absolute normalized URL from a possibly relative link."""

    return urljoin(base_url, url).strip()


def is_pdf_url(url: str) -> bool:
    """Return whether a URL likely targets a PDF file."""

    parsed = urlparse(url.lower())
    return parsed.path.endswith(".pdf") or "pdf" in parsed.query


def is_doc_url(url: str) -> bool:
    """Return whether a URL likely targets a document archive or office file."""

    parsed = urlparse(url.lower())
    return parsed.path.endswith((".doc", ".docx", ".zip"))


def is_external(url: str, base_url: str) -> bool:
    """Return whether a URL points to a different domain."""

    return urlparse(normalize_url(url, base_url)).netloc != urlparse(base_url).netloc


def url_to_filename(url: str) -> str:
    """Convert a URL path into a filesystem-friendly filename stem."""

    parsed = urlparse(url)
    name = PurePosixPath(parsed.path).name or "index"
    return name.replace("%20", "_")


def extract_domain(url: str) -> str:
    """Extract the normalized network location from a URL."""

    return urlparse(url).netloc.lower()
