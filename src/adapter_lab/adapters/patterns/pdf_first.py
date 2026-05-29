from __future__ import annotations

from datetime import UTC, datetime

from adapter_lab.adapters.base import BaseAdapter
from adapter_lab.core.models import EvidenceAsset, ExtractionResult, FetchRecord, RawCandidate
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import is_pdf_url


class PdfFirstAdapter(BaseAdapter):
    """Adapter for sources whose primary discoverable artifacts are PDFs."""

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        html = body.decode("utf-8", errors="ignore")
        links = self.html_extractor.extract_links(html, listing_url)
        pdf_links = [link for link in links if is_pdf_url(link)]
        return [
            RawCandidate(
                id=short_id(url),
                source_id=self.source_def.id,
                url=url,
                discovered_at=datetime.now(UTC),
                metadata={"listing_url": listing_url},
            )
            for url in pdf_links[:50]
        ]

    def fetch(self, candidate: RawCandidate) -> tuple[FetchRecord, list[EvidenceAsset]]:
        record, body = self.http_fetcher.fetch(
            candidate.url,
            source_id=self.source_def.id,
            candidate_id=candidate.id,
        )
        asset = self._asset_from_fetch(record, candidate.url, body)
        record.asset_ids = [asset.id]
        return record, [asset]

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        text = "\n".join(self._read_asset_text(asset) for asset in assets)
        return self._build_result(
            candidate_id="",
            combined_text=text,
            attachment_urls=[asset.original_url for asset in assets],
            raw_fields={"asset_count": len(assets)},
        )
