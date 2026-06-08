from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import urlencode, urlparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from adapter_lab.adapters.patterns.catalog_html import CatalogHtmlAdapter
from adapter_lab.core.models import (
    EvidenceAsset,
    ExtractionResult,
    FetchRecord,
    RawCandidate,
    SourceDefinition,
)
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import (
    AdapterStatus,
    AssetType,
    ExtractionStatus,
    SourceType,
)
from adapter_lab.utils.hashing import hash_content, short_id
from adapter_lab.utils.text_cleaning import normalize_italian_date
from adapter_lab.utils.urls import normalize_url


@register_adapter("incentivi_gov")
class IncentiviGovAdapter(CatalogHtmlAdapter):
    """Source adapter for incentivi.gov.it catalog pages."""

    _DEFAULT_ROWS = 200
    _MAX_ROWS = 300
    _URL_KEYS = (
        "url",
        "link",
        "permalink",
        "path",
        "path_alias",
        "alias",
        "view_node",
    )
    _TITLE_KEYS = ("title", "titolo", "name", "subject")
    _PUBLICATION_DATE_KEYS = (
        "publication_date",
        "data_pubblicazione",
        "publicationDate",
        "published_date",
        "published_at",
        "published",
        "created",
        "created_at",
    )
    _DEADLINE_KEYS = (
        "deadline",
        "deadline_date",
        "data_scadenza",
        "scadenza",
        "termine_presentazione",
        "termine",
        "data_fine",
        "end_date",
        "closing_date",
        "valid_to",
    )
    _ATTACHMENT_KEYS = (
        "attachment_urls",
        "attachments",
        "allegati",
        "files",
        "documenti",
    )
    _DISALLOWED_PATHS = {
        "/it",
        "/it/catalogo",
        "/it/chi-siamo",
        "/it/faq",
        "/it/glossario",
        "/it/open-data",
        "/it/privacy",
        "/it/note-legali",
        "/it/accessibilita",
    }
    _DISALLOWED_PREFIXES = (
        "/it/chi-siamo",
        "/it/faq",
        "/it/glossario",
        "/it/open-data",
        "/it/privacy",
        "/it/note-legali",
        "/it/accessibilita",
        "/it/scrivania",
    )
    _GENERIC_SECTION_SLUGS = {
        "incentivi",
        "incentivo",
        "misure",
        "misura",
        "bandi",
        "bando",
        "schede",
        "scheda",
        "agevolazioni",
        "agevolazione",
        "catalogo",
    }
    _DISALLOWED_LEAF_SLUGS = {
        "confronta",
    }

    source_def = SourceDefinition(
        id="incentivi_gov",
        name="Incentivi.gov.it",
        base_url=cast(HttpUrl, "https://www.incentivi.gov.it"),
        source_type=SourceType.CATALOG_HTML,
        start_urls=["https://www.incentivi.gov.it/it/catalogo"],
        tags=["italia", "nazionale", "catalogo"],
        notes="Selectors are simplified for lab prototyping. Review live structure before production promotion.",
        adapter_status=AdapterStatus.TESTING,
    )

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")
        service_config = self._parse_service_config(soup)
        endpoint_path = service_config.get("solrEndpoint")

        if endpoint_path:
            endpoint_url = normalize_url(endpoint_path, listing_url)
            query = {
                "q": "*:*",
                "rows": str(self._bounded_rows(service_config.get("solrQueryLimit"))),
                "start": "0",
                "wt": "json",
            }
            solr_url = f"{endpoint_url}?{urlencode(query)}"
            try:
                _, solr_body = self.http_fetcher.fetch(
                    solr_url, source_id=self.source_def.id
                )
                payload = json.loads(solr_body.decode("utf-8", errors="ignore"))
                docs = self._extract_docs(payload)
                candidates = self._candidates_from_docs(docs, listing_url, solr_url)
                if candidates:
                    return candidates
            except Exception:
                pass

        return self._discover_from_static_listing(soup, listing_url)

    def _parse_service_config(self, soup: BeautifulSoup) -> dict[str, str]:
        config_node = soup.select_one("script#service-config")
        if not config_node or not config_node.string:
            return {}
        try:
            entries = json.loads(config_node.string)
        except json.JSONDecodeError:
            return {}
        config: dict[str, str] = {}
        if not isinstance(entries, list):
            return config
        for item in entries:
            if not isinstance(item, Mapping):
                continue
            key = item.get("id")
            value = item.get("value")
            if isinstance(key, str) and isinstance(value, str):
                config[key] = value
        return config

    def _extract_docs(self, payload: object) -> list[Mapping[str, object]]:
        if not isinstance(payload, Mapping):
            return []
        response = payload.get("response")
        if not isinstance(response, Mapping):
            return []
        docs = response.get("docs")
        if not isinstance(docs, list):
            return []
        return [doc for doc in docs if isinstance(doc, Mapping)]

    def _candidates_from_docs(
        self,
        docs: list[Mapping[str, object]],
        listing_url: str,
        solr_url: str,
    ) -> list[RawCandidate]:
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for index, doc in enumerate(docs):
            url = self._extract_doc_url(doc, listing_url)
            if not url or url in seen:
                continue
            if not self._is_detail_url(url):
                continue
            seen.add(url)
            title = self._extract_doc_title(doc)
            doc_id = self._first_scalar(doc.get("id"))
            candidates.append(
                RawCandidate(
                    id=short_id(url),
                    source_id=self.source_def.id,
                    url=url,
                    discovered_at=datetime.now(UTC),
                    title=title,
                    metadata={
                        "listing_url": listing_url,
                        "solr_url": solr_url,
                        "solr_doc_id": doc_id,
                        "solr_doc_index": index,
                        "solr_doc": dict(doc),
                    },
                )
            )
        return candidates

    def fetch(self, candidate: RawCandidate) -> tuple[FetchRecord, list[EvidenceAsset]]:
        record, assets = super().fetch(candidate)
        solr_doc = candidate.metadata.get("solr_doc")
        if not isinstance(solr_doc, Mapping):
            return record, assets

        payload = dict(solr_doc)
        json_path = (
            self.storage.path_for_source(self.source_def.id, self.settings.raw_dir)
            / f"{candidate.id}_solr.json"
        )
        self.storage.save_json(json_path, payload)
        json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        json_asset = EvidenceAsset(
            id=short_id(f"{record.id}:solr"),
            source_id=self.source_def.id,
            fetch_record_id=record.id,
            asset_type=AssetType.JSON,
            mime_type="application/json",
            original_url=candidate.metadata.get("solr_url") or candidate.url,
            local_path=str(json_path),
            hash=hash_content(json_bytes),
            file_size=len(json_bytes),
            parent_asset_id=assets[0].id if assets else None,
            fetched_at=record.fetched_at,
        )
        assets.append(json_asset)
        record.asset_ids = [asset.id for asset in assets]
        return record, assets

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        result = super().extract(assets)
        solr_doc = self._load_solr_doc_from_assets(assets)
        if solr_doc is None:
            return result

        solr_title = self._extract_doc_title(solr_doc)
        solr_publication = self._extract_publication_date(solr_doc)
        solr_deadline = self._extract_deadline(solr_doc)
        solr_attachments = self._extract_doc_attachments(solr_doc)

        # Drop technical Solr endpoint URLs from attachment output.
        result.attachment_urls = [
            url
            for url in result.attachment_urls
            if "/solr/coredrupal/select" not in url
        ]

        source_of_truth = {
            "title": "html",
            "publication_date": "html_or_regex",
            "deadline": "html_or_regex",
            "attachment_urls": "html",
        }
        if solr_title:
            result.title = solr_title
            source_of_truth["title"] = "solr"
        if solr_publication:
            result.publication_date = solr_publication
            source_of_truth["publication_date"] = "solr"
        if solr_deadline:
            result.deadline = solr_deadline
            source_of_truth["deadline"] = "solr"
        elif not result.deadline:
            html_deadline = self._extract_deadline_from_html_assets(assets)
            if html_deadline:
                result.deadline = html_deadline
                source_of_truth["deadline"] = "html_fallback_block"
        if solr_attachments:
            merged = list(dict.fromkeys([*result.attachment_urls, *solr_attachments]))
            result.attachment_urls = merged
            source_of_truth["attachment_urls"] = "html_plus_solr"

        result.raw_fields["solr_doc"] = dict(solr_doc)
        result.raw_fields["source_of_truth"] = source_of_truth
        result.status = self._status_from_mapped_fields(result)
        return result

    def _discover_from_static_listing(
        self,
        soup: BeautifulSoup,
        listing_url: str,
    ) -> list[RawCandidate]:
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href_attr = anchor.get("href")
            if not isinstance(href_attr, str):
                continue
            href = normalize_url(href_attr, listing_url)
            if not href or href in seen or not self._is_detail_url(href):
                continue
            seen.add(href)
            candidates.append(
                RawCandidate(
                    id=short_id(href),
                    source_id=self.source_def.id,
                    url=href,
                    discovered_at=datetime.now(UTC),
                    title=anchor.get_text(" ", strip=True) or None,
                    metadata={
                        "listing_url": listing_url,
                        "discovery_mode": "static_fallback",
                    },
                )
            )
        return candidates

    def _extract_doc_url(self, doc: Mapping[str, object], base_url: str) -> str | None:
        for key in self._URL_KEYS:
            value = self._first_scalar(doc.get(key))
            if value:
                return normalize_url(value, base_url)
        for key, raw_value in doc.items():
            if "url" not in key.lower() and "path" not in key.lower():
                continue
            value = self._first_scalar(raw_value)
            if value:
                return normalize_url(value, base_url)
        return None

    def _extract_doc_title(self, doc: Mapping[str, object]) -> str | None:
        for key in self._TITLE_KEYS:
            value = self._first_scalar(doc.get(key))
            if value:
                return value
        for key, raw_value in doc.items():
            if "title" not in key.lower() and "titolo" not in key.lower():
                continue
            value = self._first_scalar(raw_value)
            if value:
                return value
        return None

    def _is_detail_url(self, url: str) -> bool:
        path = urlparse(url).path.lower().rstrip("/") or "/"
        if not path.startswith("/it"):
            return False
        if path in self._DISALLOWED_PATHS:
            return False

        if any(
            path == prefix or path.startswith(f"{prefix}/")
            for prefix in self._DISALLOWED_PREFIXES
        ):
            return False

        segments = [segment for segment in path.split("/") if segment]
        if len(segments) < 2:
            return False

        leaf = segments[-1]
        if leaf in self._DISALLOWED_LEAF_SLUGS:
            return False

        if leaf in self._GENERIC_SECTION_SLUGS:
            return False

        if path.startswith("/it/catalogo/"):
            # Catalog detail pages are canonical for this source.
            return True

        # Outside /it/catalogo/, require at least /it/<section>/<detail-slug>.
        if len(segments) < 3:
            return False

        return any(
            token in path
            for token in ("incentiv", "misura", "agevolaz", "bando", "scheda")
        )

    def _first_scalar(self, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, Mapping):
            for key in ("value", "date", "data", "timestamp", "text"):
                nested = self._first_scalar(value.get(key))
                if nested:
                    return nested
            for nested_value in value.values():
                nested = self._first_scalar(nested_value)
                if nested:
                    return nested
        if isinstance(value, list):
            for item in value:
                result = self._first_scalar(item)
                if result:
                    return result
        return None

    def _load_solr_doc_from_assets(
        self,
        assets: list[EvidenceAsset],
    ) -> Mapping[str, object] | None:
        for asset in assets:
            if asset.asset_type != AssetType.JSON:
                continue
            try:
                payload = json.loads(Path(asset.local_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, Mapping):
                return payload
        return None

    def _extract_publication_date(self, doc: Mapping[str, object]) -> str | None:
        value = self._extract_date_with_aliases(doc, self._PUBLICATION_DATE_KEYS)
        if value:
            return value
        for key, raw_value in doc.items():
            lower_key = key.lower()
            if (
                "pubblic" not in lower_key
                and "created" not in lower_key
                and "publish" not in lower_key
                and "data_pub" not in lower_key
            ):
                continue
            value = self._normalize_date(self._first_scalar(raw_value))
            if value:
                return value
        return None

    def _extract_deadline(self, doc: Mapping[str, object]) -> str | None:
        value = self._extract_date_with_aliases(doc, self._DEADLINE_KEYS)
        if value:
            return value
        for key, raw_value in doc.items():
            lower_key = key.lower()
            if (
                "scaden" not in lower_key
                and "termine" not in lower_key
                and "deadline" not in lower_key
                and "closing" not in lower_key
                and "end_date" not in lower_key
                and "valid_to" not in lower_key
            ):
                continue
            value = self._normalize_date(self._first_scalar(raw_value))
            if value:
                return value
        return None

    def _extract_date_with_aliases(
        self, doc: Mapping[str, object], keys: tuple[str, ...]
    ) -> str | None:
        for key in keys:
            value = self._normalize_date(self._first_scalar(doc.get(key)))
            if value:
                return value
        return None

    def _extract_doc_attachments(self, doc: Mapping[str, object]) -> list[str]:
        urls: list[str] = []
        for key in self._ATTACHMENT_KEYS:
            urls.extend(self._normalize_attachment_values(doc.get(key)))
        if urls:
            return list(dict.fromkeys(urls))
        for key, raw_value in doc.items():
            lower_key = key.lower()
            if (
                "alleg" not in lower_key
                and "attach" not in lower_key
                and "file" not in lower_key
            ):
                continue
            urls.extend(self._normalize_attachment_values(raw_value))
        return list(dict.fromkeys(urls))

    def _normalize_attachment_values(self, value: object) -> list[str]:
        if isinstance(value, str):
            return (
                [normalize_url(value, str(self.source_def.base_url))]
                if value.strip()
                else []
            )
        if isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                normalized.extend(self._normalize_attachment_values(item))
            return normalized
        if isinstance(value, Mapping):
            for key in ("url", "href", "link"):
                normalized = self._normalize_attachment_values(value.get(key))
                if normalized:
                    return normalized
        return []

    def _normalize_date(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) >= 10:
            candidate = cleaned[:10]
            if candidate[4:5] == "-" and candidate[7:8] == "-":
                return candidate
        return normalize_italian_date(cleaned)

    def _extract_deadline_from_html_assets(
        self, assets: list[EvidenceAsset]
    ) -> str | None:
        for asset in assets:
            if asset.asset_type != AssetType.HTML:
                continue
            try:
                html = Path(asset.local_path).read_text(
                    encoding="utf-8", errors="ignore"
                )
            except OSError:
                continue
            deadline = self._extract_deadline_from_html(html)
            if deadline:
                return deadline
        return None

    def _extract_deadline_from_html(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")

        # Definition lists are common in institutional pages with field/value pairs.
        for dt in soup.select("dt"):
            label = dt.get_text(" ", strip=True).lower()
            if not self._looks_like_deadline_label(label):
                continue
            dd = dt.find_next_sibling("dd")
            if dd:
                deadline = self._extract_date_from_text(dd.get_text(" ", strip=True))
                if deadline:
                    return deadline

        # Table rows often carry labels like "Scadenza" and related dates.
        for row in soup.select("tr"):
            text = row.get_text(" ", strip=True)
            if not self._looks_like_deadline_label(text.lower()):
                continue
            deadline = self._extract_date_from_text(text)
            if deadline:
                return deadline

        # Generic fallback on paragraphs/list items with deadline-like labels.
        for node in soup.select("p, li, div"):
            text = node.get_text(" ", strip=True)
            if not self._looks_like_deadline_label(text.lower()):
                continue
            deadline = self._extract_date_from_text(text)
            if deadline:
                return deadline
        return None

    def _looks_like_deadline_label(self, text: str) -> bool:
        return any(
            token in text
            for token in (
                "scadenza",
                "termine",
                "presentazione domande",
                "presentazione della domanda",
                "entro il",
                "fino al",
            )
        )

    def _extract_date_from_text(self, text: str) -> str | None:
        patterns = (
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
            (
                r"(\d{1,2}\s+"
                r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
                r"luglio|agosto|settembre|ottobre|novembre|dicembre)"
                r"\s+\d{4})"
            ),
        )
        lowered = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if not match:
                continue
            raw = match.group(1).replace(".", "/")
            normalized = self._normalize_date(raw)
            if normalized:
                return normalized
        return None

    def _status_from_mapped_fields(self, result: ExtractionResult) -> ExtractionStatus:
        if not result.title:
            return ExtractionStatus.FAILED
        if result.deadline:
            return ExtractionStatus.SUCCESS
        if result.publication_date or result.attachment_urls:
            return ExtractionStatus.SUCCESS
        return ExtractionStatus.PARTIAL

    def _bounded_rows(self, configured_rows: str | None) -> int:
        if configured_rows is None:
            return self._DEFAULT_ROWS
        try:
            rows = int(configured_rows)
        except ValueError:
            return self._DEFAULT_ROWS
        rows = max(1, rows)
        return min(rows, self._MAX_ROWS)
