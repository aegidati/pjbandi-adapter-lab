from __future__ import annotations

import httpx

from adapter_lab.core.models import SourceProfile
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.types import SourceType
from adapter_lab.extractors.html_extractors import HtmlExtractor
from adapter_lab.utils.text_cleaning import truncate
from adapter_lab.utils.urls import extract_domain, is_pdf_url


class SourceAnalyzer:
    """Analyze a public funding source page without requiring an LLM."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.html_extractor = HtmlExtractor()

    def analyze(self, url: str) -> SourceProfile:
        """Analyze a starting URL and return a source profile."""

        html = self._fetch_page(url)
        links = self._extract_candidate_links(html, url)
        pagination = self._detect_pagination(html, url)
        attachments = self._detect_attachments(html)
        source_id = extract_domain(url).replace(".", "_").replace("-", "_") or "unknown_source"
        notes = [
            f"Detected {len(links)} candidate links",
            f"Detected {len(attachments)} attachment links",
        ]
        return SourceProfile(
            source_id=source_id,
            analyzed_url=url,
            inferred_type=self._detect_source_type(html, url),
            title=self.html_extractor.extract_title(html),
            description=self.html_extractor.extract_meta_description(html),
            detected_links=links,
            pagination_pattern=pagination,
            attachment_links=attachments,
            candidate_count_estimate=len(links),
            notes=notes,
        )

    def _fetch_page(self, url: str) -> str:
        """Fetch a page and return it as text."""

        with httpx.Client(
            follow_redirects=True,
            timeout=self.settings.http_timeout,
            headers={"User-Agent": self.settings.user_agent},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
        return response.text

    def _detect_source_type(self, html: str, url: str) -> SourceType:
        """Infer the likely source type from the page shape."""

        lower_html = html.lower()
        if "application/json" in lower_html or "api/" in url:
            return SourceType.API_BACKED
        if ".pdf" in lower_html and ("bando" in lower_html or "allegato" in lower_html):
            return SourceType.REGIONAL_HTML_PDF
        if is_pdf_url(url):
            return SourceType.PDF_FIRST
        if "gazzetta" in lower_html or "bollettino" in lower_html or "bur" in lower_html:
            return SourceType.LEGAL_BULLETIN
        if "<a " in lower_html:
            return SourceType.CATALOG_HTML
        return SourceType.UNKNOWN

    def _extract_candidate_links(self, html: str, base_url: str) -> list[str]:
        """Extract likely candidate detail links from a page."""

        links = self.html_extractor.extract_links(html, base_url)
        keywords = ("bando", "avviso", "scheda", "opportun", "contribut", "incentiv")
        filtered = [link for link in links if any(keyword in link.lower() for keyword in keywords)]
        return filtered or links[:25]

    def _detect_pagination(self, html: str, base_url: str) -> str | None:
        """Detect a pagination pattern when present."""

        links = self.html_extractor.extract_links(html, base_url)
        for link in links:
            if "page=" in link.lower() or "/page/" in link.lower():
                return truncate(link, 200)
        lower_html = html.lower()
        if "pagina successiva" in lower_html or "next" in lower_html:
            return "next-link-detected"
        return None

    def _detect_attachments(self, html: str) -> list[str]:
        """Detect likely attachment links from the source page."""

        attachments = []
        for token in html.split('"'):
            candidate = token.strip()
            if candidate.lower().endswith((".pdf", ".doc", ".docx", ".zip")):
                attachments.append(candidate)
        seen: set[str] = set()
        ordered: list[str] = []
        for attachment in attachments:
            if attachment not in seen:
                seen.add(attachment)
                ordered.append(attachment)
        return ordered
