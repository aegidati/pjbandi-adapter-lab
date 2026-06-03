from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from adapter_lab.adapters.patterns.catalog_html import CatalogHtmlAdapter
from adapter_lab.core.models import (
    EvidenceAsset,
    ExtractionResult,
    RawCandidate,
    SourceDefinition,
)
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import AdapterStatus, ExtractionStatus, SourceType
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.text_cleaning import clean_whitespace, normalize_italian_date
from adapter_lab.utils.urls import normalize_url

_DETAIL_PATH_PREFIX = "/incentivi-e-strumenti/"
_LISTING_PATH = "/per-le-imprese/incentivi-e-strumenti"
_MAX_DISCOVERY_PAGES = 30
_OPEN_LABEL_RE = re.compile(r"data\s+apertura[^\d]*([^\n\r]+)", re.IGNORECASE)
_CLOSE_LABEL_RE = re.compile(r"data\s+chiusura[^\d]*([^\n\r]+)", re.IGNORECASE)
_DETAIL_TITLE_PREFIX_RE = re.compile(r"^leggi\s+tutto\s+su\s+", re.IGNORECASE)
_DETAIL_TITLE_SUFFIX_RE = re.compile(
    r"\s+(attivo|in apertura|chiuso|sospeso)$",
    re.IGNORECASE,
)
_API_ENDPOINT_RE = re.compile(
    (
        r"(https?://[^\"'\s>]+(?:api|json)[^\"'\s>]*)"
        r"|"
        r"(/[\w\-/%.?=&]*(?:api|json)[\w\-/%.?=&]*)"
    ),
    re.IGNORECASE,
)
_DATE_CANDIDATES_RE = re.compile(
    (
        r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
        r"\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
        r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4})"
    ),
    re.IGNORECASE,
)


@register_adapter("invitalia")
class InvitaliaAdapter(CatalogHtmlAdapter):
    """Source adapter for Invitalia incentives and instruments catalog."""

    source_def = SourceDefinition(
        id="invitalia",
        name="Invitalia Incentivi e Strumenti",
        base_url=cast(HttpUrl, "https://www.invitalia.it"),
        source_type=SourceType.CATALOG_HTML,
        start_urls=["https://www.invitalia.it/per-le-imprese/incentivi-e-strumenti"],
        tags=["italia", "nazionale", "invitalia", "incentivi"],
        notes=(
            "Discovery paginata con strategia JSON-first (script embedded) "
            "e fallback HTML links."
        ),
        adapter_status=AdapterStatus.TESTING,
    )

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, first_body = self.http_fetcher.fetch(
            self._page_url(listing_url, 0),
            source_id=self.source_def.id,
        )
        first_soup = BeautifulSoup(first_body.decode("utf-8", errors="ignore"), "lxml")
        direct_api_candidates = self._discover_from_direct_api(first_soup, listing_url)
        if direct_api_candidates:
            return direct_api_candidates

        candidates: list[RawCandidate] = []
        seen: set[str] = set()

        for page_index in range(_MAX_DISCOVERY_PAGES):
            page_url = self._page_url(listing_url, page_index)
            if page_index == 0:
                soup = first_soup
            else:
                _, body = self.http_fetcher.fetch(
                    page_url, source_id=self.source_def.id
                )
                soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")

            page_candidates = self._discover_from_json_scripts(
                soup,
                page_url,
                page_index,
            )
            if not page_candidates:
                page_candidates = self._discover_from_listing_html(
                    soup,
                    page_url,
                    page_index,
                )

            new_on_page = 0
            for candidate in page_candidates:
                if candidate.url in seen:
                    continue
                seen.add(candidate.url)
                candidates.append(candidate)
                new_on_page += 1

            if not self._has_next_page(soup, page_index):
                break
            if page_index > 0 and new_on_page == 0:
                break

        return candidates

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        result = super().extract(assets)
        html_asset = next(
            (asset for asset in assets if asset.asset_type.value == "html"),
            None,
        )
        if html_asset is None:
            return result

        html = Path(html_asset.local_path).read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")
        title_node = soup.select_one("h1")
        if title_node:
            title = clean_whitespace(title_node.get_text(" ", strip=True))
            if title:
                result.title = self._clean_candidate_title(title)

        full_text = clean_whitespace(soup.get_text(" ", strip=True))
        publication_date = self._extract_labeled_date(full_text, _OPEN_LABEL_RE)
        deadline = self._extract_labeled_date(full_text, _CLOSE_LABEL_RE)
        if publication_date:
            result.publication_date = publication_date
        if deadline:
            result.deadline = deadline

        result.status = self._status_from_mapped_fields(result)
        result.raw_fields["source_of_truth"] = {
            "title": "html",
            "publication_date": "html_label_or_regex",
            "deadline": "html_label_or_regex",
            "attachment_urls": "html",
        }
        return result

    def _discover_from_json_scripts(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_index: int,
    ) -> list[RawCandidate]:
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for script in soup.select(
            'script[type="application/ld+json"], script[type="application/json"]'
        ):
            script_body = script.string
            if not script_body:
                continue
            try:
                payload = json.loads(script_body)
            except json.JSONDecodeError:
                continue
            for node in self._iter_json_nodes(payload):
                raw_url = self._first_scalar(
                    node.get("url")
                    or node.get("link")
                    or node.get("href")
                    or node.get("path")
                )
                if not raw_url:
                    continue
                normalized_url = self._normalize_detail_url(raw_url, page_url)
                if not normalized_url or normalized_url in seen:
                    continue
                seen.add(normalized_url)
                title = self._first_scalar(
                    node.get("name") or node.get("title") or node.get("headline")
                )
                cleaned_title = self._clean_candidate_title(title)
                candidates.append(
                    RawCandidate(
                        id=short_id(normalized_url),
                        source_id=self.source_def.id,
                        url=normalized_url,
                        discovered_at=datetime.now(UTC),
                        title=cleaned_title,
                        metadata={
                            "listing_url": page_url,
                            "page": page_index,
                            "discovery_mode": "json_script",
                        },
                    )
                )
        return candidates

    def _discover_from_listing_html(
        self,
        soup: BeautifulSoup,
        page_url: str,
        page_index: int,
    ) -> list[RawCandidate]:
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            normalized_url = self._normalize_detail_url(href_attr, page_url)
            if not normalized_url or normalized_url in seen:
                continue
            seen.add(normalized_url)
            label = clean_whitespace(anchor.get_text(" ", strip=True)) or None
            cleaned_label = self._clean_candidate_title(label)
            candidates.append(
                RawCandidate(
                    id=short_id(normalized_url),
                    source_id=self.source_def.id,
                    url=normalized_url,
                    discovered_at=datetime.now(UTC),
                    title=cleaned_label,
                    metadata={
                        "listing_url": page_url,
                        "page": page_index,
                        "discovery_mode": "html",
                    },
                )
            )
        return candidates

    def _normalize_detail_url(self, raw_url: str, base_url: str) -> str | None:
        normalized = normalize_url(raw_url, base_url)
        parsed = urlparse(normalized)
        if parsed.netloc != urlparse(str(self.source_def.base_url)).netloc:
            return None
        if not self._is_detail_path(parsed.path):
            return None

        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() != "from"
        ]
        canonical = parsed._replace(
            query=urlencode(filtered_query, doseq=True),
            fragment="",
        )
        return urlunparse(canonical)

    def _is_detail_path(self, path: str) -> bool:
        normalized = path.lower().rstrip("/")
        if normalized == _LISTING_PATH:
            return False
        return normalized.startswith(_DETAIL_PATH_PREFIX.rstrip("/"))

    def _has_next_page(self, soup: BeautifulSoup, page_index: int) -> bool:
        next_page_marker = f"page={page_index + 1}"
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            if next_page_marker in href_attr:
                return True
        return False

    def _page_url(self, listing_url: str, page: int) -> str:
        parsed = urlparse(listing_url)
        query = [
            (key, value) for key, value in parse_qsl(parsed.query) if key != "page"
        ]
        query.append(("page", str(page)))
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def _extract_labeled_date(self, text: str, pattern: re.Pattern[str]) -> str | None:
        match = pattern.search(text)
        if not match:
            return None
        fragment = match.group(1)
        for date_match in _DATE_CANDIDATES_RE.finditer(fragment):
            normalized = normalize_italian_date(date_match.group(1).replace(".", "/"))
            if normalized:
                return normalized
        return None

    def _iter_json_nodes(self, payload: object):
        if isinstance(payload, Mapping):
            yield payload
            for value in payload.values():
                yield from self._iter_json_nodes(value)
            return
        if isinstance(payload, list):
            for item in payload:
                yield from self._iter_json_nodes(item)

    def _discover_from_direct_api(
        self,
        soup: BeautifulSoup,
        listing_url: str,
    ) -> list[RawCandidate]:
        candidates: list[RawCandidate] = []
        seen: set[str] = set()

        endpoints = self._extract_api_endpoints(soup, listing_url)
        for endpoint in endpoints:
            try:
                _, body = self.http_fetcher.fetch(
                    endpoint, source_id=self.source_def.id
                )
                payload = json.loads(body.decode("utf-8", errors="ignore"))
            except Exception:
                continue

            for node in self._iter_json_nodes(payload):
                raw_url = self._first_scalar(
                    node.get("url")
                    or node.get("link")
                    or node.get("href")
                    or node.get("path")
                )
                if not raw_url:
                    continue

                normalized_url = self._normalize_detail_url(raw_url, listing_url)
                if not normalized_url or normalized_url in seen:
                    continue
                seen.add(normalized_url)

                raw_title = self._first_scalar(
                    node.get("name") or node.get("title") or node.get("headline")
                )
                candidates.append(
                    RawCandidate(
                        id=short_id(normalized_url),
                        source_id=self.source_def.id,
                        url=normalized_url,
                        discovered_at=datetime.now(UTC),
                        title=self._clean_candidate_title(raw_title),
                        metadata={
                            "listing_url": listing_url,
                            "discovery_mode": "direct_api",
                            "api_endpoint": endpoint,
                        },
                    )
                )

        return candidates

    def _extract_api_endpoints(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        endpoints: list[str] = []
        for script in soup.select("script"):
            body = script.string or script.get_text(" ", strip=True)
            if not body:
                continue
            for match in _API_ENDPOINT_RE.finditer(body):
                token = match.group(1) or match.group(2)
                if not token:
                    continue
                normalized = normalize_url(token, base_url)
                parsed = urlparse(normalized)
                if parsed.netloc != urlparse(str(self.source_def.base_url)).netloc:
                    continue
                endpoints.append(normalized)
        # Preserve order while deduplicating.
        return list(dict.fromkeys(endpoints))

    def _clean_candidate_title(self, title: str | None) -> str | None:
        if not title:
            return None
        cleaned = clean_whitespace(title)
        if not cleaned:
            return None
        cleaned = _DETAIL_TITLE_PREFIX_RE.sub("", cleaned)
        cleaned = _DETAIL_TITLE_SUFFIX_RE.sub("", cleaned)
        cleaned = clean_whitespace(cleaned)
        return cleaned or None

    def _first_scalar(self, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = clean_whitespace(value)
            return cleaned or None
        if isinstance(value, list):
            for item in value:
                scalar = self._first_scalar(item)
                if scalar:
                    return scalar
        if isinstance(value, Mapping):
            for key in ("value", "text", "name", "title"):
                scalar = self._first_scalar(value.get(key))
                if scalar:
                    return scalar
        return None

    def _status_from_mapped_fields(self, result: ExtractionResult) -> ExtractionStatus:
        if not result.title:
            return ExtractionStatus.FAILED
        if result.deadline:
            return ExtractionStatus.SUCCESS
        if result.publication_date or result.attachment_urls:
            return ExtractionStatus.SUCCESS
        return ExtractionStatus.PARTIAL
