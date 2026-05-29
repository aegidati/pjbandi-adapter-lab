from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.base import BaseAdapter
from adapter_lab.core.models import EvidenceAsset, ExtractionResult, FetchRecord, RawCandidate
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import is_doc_url, is_pdf_url


class CatalogHtmlAdapter(BaseAdapter):
    """Adapter for sources exposing a catalog or listing page in HTML."""

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        html = body.decode("utf-8", errors="ignore")
        links = self.html_extractor.extract_links(html, listing_url)
        keywords = ("bando", "avviso", "scheda", "opportun", "contribut", "agevol", "incentiv")
        filtered = [
            link
            for link in links
            if not is_pdf_url(link)
            and not is_doc_url(link)
            and any(key in link.lower() for key in keywords)
        ]
        candidate_links = filtered or [
            link for link in links if not is_pdf_url(link) and not is_doc_url(link)
        ]
        return [
            RawCandidate(
                id=short_id(url),
                source_id=self.source_def.id,
                url=url,
                discovered_at=datetime.now(UTC),
                metadata={"listing_url": listing_url},
            )
            for url in candidate_links[:50]
        ]

    def fetch(self, candidate: RawCandidate) -> tuple[FetchRecord, list[EvidenceAsset]]:
        record, body = self.http_fetcher.fetch(
            candidate.url,
            source_id=self.source_def.id,
            candidate_id=candidate.id,
        )
        main_asset = self._asset_from_fetch(record, candidate.url, body)
        assets = [main_asset]
        if main_asset.asset_type.value == "html":
            html = body.decode("utf-8", errors="ignore")
            assets.extend(
                self._download_linked_assets(html, candidate.url, parent_asset_id=main_asset.id)
            )
        record.asset_ids = [asset.id for asset in assets]
        return record, assets

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        html_asset = next((asset for asset in assets if asset.asset_type.value == "html"), None)
        pdf_assets = [asset for asset in assets if asset.asset_type.value == "pdf"]
        title = None
        text_parts: list[str] = []
        if html_asset:
            html = Path(html_asset.local_path).read_text(encoding="utf-8", errors="ignore")
            title = self.html_extractor.extract_title(html)
            text_parts.append(self.html_extractor.extract_text(html))
        for asset in pdf_assets:
            text_parts.append(self._read_asset_text(asset))
        attachment_urls = [asset.original_url for asset in assets if asset is not html_asset]
        return self._build_result(
            candidate_id="",
            combined_text="\n".join(part for part in text_parts if part),
            attachment_urls=attachment_urls,
            title=title,
            raw_fields={"asset_count": len(assets), "has_pdf": bool(pdf_assets)},
        )
