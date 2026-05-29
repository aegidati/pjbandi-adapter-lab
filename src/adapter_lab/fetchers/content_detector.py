from __future__ import annotations

import json

from adapter_lab.core.types import AssetType
from adapter_lab.utils.urls import is_pdf_url


class ContentDetector:
    """Infer asset types from headers, URLs, and content bytes."""

    def detect_type(self, content_type: str | None, url: str, content: bytes) -> AssetType:
        """Return the best matching asset type for a fetched payload."""

        if self.is_pdf(content_type, url) or content.startswith(b"%PDF"):
            return AssetType.PDF
        if self.is_json(content_type):
            return AssetType.JSON
        if self.is_html(content_type) or b"<html" in content[:500].lower():
            return AssetType.HTML
        lower_url = url.lower()
        if lower_url.endswith(".docx"):
            return AssetType.DOCX
        if lower_url.endswith(".zip"):
            return AssetType.ZIP
        try:
            json.loads(content.decode("utf-8"))
            return AssetType.JSON
        except Exception:
            return AssetType.OTHER

    def is_pdf(self, content_type: str | None, url: str) -> bool:
        """Return whether the response is likely a PDF."""

        return "pdf" in (content_type or "").lower() or is_pdf_url(url)

    def is_html(self, content_type: str | None) -> bool:
        """Return whether the response is likely HTML."""

        return "html" in (content_type or "").lower()

    def is_json(self, content_type: str | None) -> bool:
        """Return whether the response is likely JSON."""

        lowered = (content_type or "").lower()
        return "json" in lowered or "javascript" in lowered
