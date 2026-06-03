from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from adapter_lab.adapters.patterns.regional_html_pdf import (
    RegionalHtmlPdfAdapter,
)
from adapter_lab.core.models import (
    EvidenceAsset,
    ExtractionResult,
    FetchRecord,
    RawCandidate,
    SourceDefinition,
)
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import AdapterStatus, ExtractionStatus, SourceType
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.text_cleaning import (
    clean_whitespace,
    normalize_italian_date,
)
from adapter_lab.utils.urls import normalize_url

# Tokens that signal a URL leads to a bando detail page on this portal.
_DETAIL_TOKENS = ("dettaglio", "bando", "scheda", "avviso")
_PORTAL_TITLE = "Portale Bandi Avvisi Concorsi - Regione del Veneto"
_DEADLINE_LABEL_RE = re.compile(r"\b(scadenza|termine)\b", re.IGNORECASE)
_PUBLICATION_LABEL_RE = re.compile(r"\bpubblicazione\b", re.IGNORECASE)


@register_adapter("veneto_bandi")
class VenetoBandiAdapter(RegionalHtmlPdfAdapter):
    """Source adapter for bandi.regione.veneto.it.

    Entry point: /Public/Index (portal home).
    Listing page: /Public/Elenco (all open and recent calls).
    Detail pages: identified by URL tokens such as 'Dettaglio' or 'Scheda'.

    Assumptions:
        - Detail page URLs contain at least one of:
            dettaglio, bando, scheda, avviso.
    - PDF attachments are linked from each detail page.
    - Pagination URL pattern is unknown and not yet handled; limit discovery to
    the first listing page until the pattern is
    confirmed with a live fixture.
    """

    # The listing URL is kept explicit so discover() does not depend on
    # start_urls ordering and the entry point can be documented separately.
    _LISTING_URL = "https://bandi.regione.veneto.it/Public/Elenco"

    source_def = SourceDefinition(
        id="veneto_bandi",
        name="Bandi Regione Veneto",
        base_url=cast(HttpUrl, "https://bandi.regione.veneto.it"),
        source_type=SourceType.REGIONAL_HTML_PDF,
        start_urls=[
            "https://bandi.regione.veneto.it/Public/Index",
            "https://bandi.regione.veneto.it/Public/Elenco",
        ],
        tags=["veneto", "regione", "bandi"],
        notes=(
            "Entry point: /Public/Index. "
            "Listing at /Public/Elenco. "
            "Detail pages identified by URL tokens (dettaglio, scheda). "
            "Pagination structure unverified; promote to STABLE "
            "after live fixture validation."
        ),
        adapter_status=AdapterStatus.TESTING,
    )

    def discover(self) -> list[RawCandidate]:
        """Discover bando detail URLs from the Veneto portal listing page."""
        listing_url = self._LISTING_URL
        _, body = self.http_fetcher.fetch(
            listing_url,
            source_id=self.source_def.id,
        )
        soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            href = normalize_url(href_attr, listing_url)
            if not href or href in seen:
                continue
            if any(token in href.lower() for token in _DETAIL_TOKENS):
                seen.add(href)
                label = anchor.get_text(" ", strip=True)
                candidates.append(
                    RawCandidate(
                        id=short_id(href),
                        source_id=self.source_def.id,
                        url=href,
                        discovered_at=datetime.now(UTC),
                        title=label or None,
                        metadata={
                            "listing_url": listing_url,
                            "region": "veneto",
                        },
                    )
                )
        return candidates or super().discover()

    def fetch(
        self,
        candidate: RawCandidate,
    ) -> tuple[FetchRecord, list[EvidenceAsset]]:
        """Fetch detail HTML and include Veneto attachments."""

        record, body = self.http_fetcher.fetch(
            candidate.url,
            source_id=self.source_def.id,
            candidate_id=candidate.id,
        )
        main_asset = self._asset_from_fetch(record, candidate.url, body)
        assets = [main_asset]
        html = body.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")
        attachment_urls: list[str] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            href = normalize_url(href_attr, candidate.url)
            if not href or href in seen:
                continue
            if self._is_attachment_url(href):
                seen.add(href)
                attachment_urls.append(href)
        if attachment_urls:
            downloaded = self.download_manager.download_many(
                attachment_urls,
                self.source_def.id,
            )
            for asset in downloaded:
                asset.parent_asset_id = main_asset.id
                assets.append(asset)
        record.asset_ids = [asset.id for asset in assets]
        return record, assets

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        """Extract structured fields from fetched Veneto evidence assets."""
        result = super().extract(assets)
        html_asset = next(
            (asset for asset in assets if asset.asset_type.value == "html"),
            None,
        )
        if html_asset:
            html = Path(html_asset.local_path).read_text(
                encoding="utf-8", errors="ignore"
            )
            soup = BeautifulSoup(html, "lxml")
            contextual_title = self._extract_specific_title(soup)
            if contextual_title:
                result.title = contextual_title
            attachment_urls = [
                asset.original_url
                for asset in assets
                if asset.asset_type.value != "html"
            ]
            if attachment_urls:
                result.attachment_urls = list(dict.fromkeys(attachment_urls))
                result.raw_fields["pdf_count"] = sum(
                    1 for asset in assets if asset.asset_type.value == "pdf"
                )
            publication_date = self._extract_publication_date(soup)
            if publication_date:
                result.publication_date = publication_date
            # For Veneto pages we only trust context-aware deadline extraction.
            result.deadline = self._extract_deadline(soup)
            if not result.deadline:
                result.status = ExtractionStatus.PARTIAL
            # Try to capture the emitting authority in portal HTML.
            authority_node = soup.select_one(
                ".ente-emittente, .autorita, [class*='autorita']"
            ) or self._labeled_field_node(soup, "struttura")
            if authority_node:
                result.raw_fields["authority"] = authority_node.get_text(
                    " ", strip=True
                )
            if "veneto" in html.lower():
                result.extraction_notes.append(
                    "Detected Veneto-specific branding in HTML evidence."
                )
        return result

    def _is_attachment_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parsed.query.lower()
        if path.endswith((".pdf", ".doc", ".docx", ".zip")):
            return True
        if "/public/download" in path and "idallegato=" in query:
            return True
        if "pdf" in query:
            return True
        return False

    def _labeled_field_node(self, soup: BeautifulSoup, label: str):
        normalized = label.lower()
        for node in soup.select(".display-label"):
            text = clean_whitespace(node.get_text(" ", strip=True)).rstrip(":").lower()
            if text == normalized:
                sibling = node.find_next_sibling()
                while sibling is not None:
                    classes = sibling.get("class")
                    if isinstance(classes, list) and "display-field" in classes:
                        value = clean_whitespace(sibling.get_text(" ", strip=True))
                        if value:
                            return sibling
                    sibling = sibling.find_next_sibling()
                container = node.find_parent(class_="rowContainer")
                if not container:
                    continue
                for field in container.select(".display-field"):
                    value = clean_whitespace(field.get_text(" ", strip=True))
                    if value:
                        return field
        return None

    def _extract_specific_title(self, soup: BeautifulSoup) -> str | None:
        labeled = self._labeled_field_node(soup, "titolo")
        if labeled:
            return clean_whitespace(labeled.get_text(" ", strip=True))
        for node in soup.select("h1"):
            style = str(node.get("style") or "").lower()
            text = clean_whitespace(node.get_text(" ", strip=True))
            if not text:
                continue
            if "display: none" in style:
                continue
            if text == _PORTAL_TITLE:
                continue
            return text
        meta_title = soup.select_one('meta[property="og:title"], meta[itemprop="name"]')
        if meta_title:
            content = meta_title.get("content")
            if isinstance(content, str) and content:
                return clean_whitespace(content)
        title_tag = soup.select_one("title")
        if title_tag:
            return clean_whitespace(title_tag.get_text(" ", strip=True))
        return None

    def _extract_publication_date(self, soup: BeautifulSoup) -> str | None:
        labeled = self._labeled_field_node(soup, "pubblicazione")
        if labeled:
            return normalize_italian_date(labeled.get_text(" ", strip=True))
        for node in soup.find_all(["div", "p", "span", "li"]):
            text = clean_whitespace(node.get_text(" ", strip=True))
            if not text:
                continue
            if _PUBLICATION_LABEL_RE.search(text):
                parsed = normalize_italian_date(text)
                if parsed:
                    return parsed
        return None

    def _extract_deadline(self, soup: BeautifulSoup) -> str | None:
        labeled = self._labeled_field_node(soup, "scadenza")
        if labeled:
            return normalize_italian_date(labeled.get_text(" ", strip=True))
        for node in soup.find_all(["div", "p", "span", "li"]):
            text = clean_whitespace(node.get_text(" ", strip=True))
            if not text:
                continue
            if "scadenzario" in text.lower():
                continue
            if _DEADLINE_LABEL_RE.search(text):
                parsed = normalize_italian_date(text)
                if parsed:
                    return parsed
        return None
