from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from adapter_lab.adapters.patterns.regional_html_pdf import RegionalHtmlPdfAdapter
from adapter_lab.core.models import RawCandidate, SourceDefinition
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import AdapterStatus, SourceType
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import normalize_url

_MIMIT_PAGE_SIZE = 20
_MIMIT_MAX_PAGES = 20


@register_adapter("mimit")
class MimitAdapter(RegionalHtmlPdfAdapter):
    """Source adapter for MIMIT funding and incentive pages."""

    source_def = SourceDefinition(
        id="mimit",
        name="Ministero delle Imprese e del Made in Italy",
        base_url=cast(HttpUrl, "https://www.mimit.gov.it"),
        source_type=SourceType.REGIONAL_HTML_PDF,
        start_urls=["https://www.mimit.gov.it/it/incentivi"],
        tags=["ministero", "italia", "incentivi"],
        notes="Specific selectors should be reviewed against representative MIMIT fixtures.",
        adapter_status=AdapterStatus.TESTING,
    )

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        candidates: list[RawCandidate] = []
        seen: set[str] = set()

        for page in range(_MIMIT_MAX_PAGES):
            page_start = page * _MIMIT_PAGE_SIZE
            page_url = self._page_url(listing_url, page_start)
            _, body = self.http_fetcher.fetch(page_url, source_id=self.source_def.id)
            soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")

            page_candidates = list(self._discover_from_page(soup, page_url, page_start))
            new_on_page = 0
            for candidate in page_candidates:
                if candidate.url in seen:
                    continue
                seen.add(candidate.url)
                candidates.append(candidate)
                new_on_page += 1

            if not self._has_next_page(soup, page_start):
                break
            if page > 0 and new_on_page == 0:
                break

        return candidates or super().discover()

    def _discover_from_page(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_start: int,
    ) -> Iterable[RawCandidate]:
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            candidate_url = normalize_url(href_attr, page_url)
            if not self._is_candidate_url(candidate_url):
                continue

            title = anchor.get_text(" ", strip=True) or None
            yield RawCandidate(
                id=short_id(candidate_url),
                source_id=self.source_def.id,
                url=candidate_url,
                discovered_at=datetime.now(UTC),
                title=title,
                metadata={
                    "listing_url": page_url,
                    "page_start": page_start,
                    "discovery_mode": "html_paginated",
                },
            )

    def _is_candidate_url(self, url: str) -> bool:
        parsed = urlparse(url)
        base_host = urlparse(str(self.source_def.base_url)).netloc
        if parsed.netloc != base_host:
            return False
        path = parsed.path.rstrip("/")
        if path == "/it/incentivi":
            return False
        return path.startswith("/it/incentivi/")

    def _page_url(self, listing_url: str, start: int) -> str:
        parsed = urlparse(listing_url)
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "start"]
        if start > 0:
            query.append(("start", str(start)))
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def _has_next_page(self, soup: BeautifulSoup, current_start: int) -> bool:
        next_start = current_start + _MIMIT_PAGE_SIZE
        next_marker = f"start={next_start}"
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            if next_marker in href_attr:
                return True
        return False
