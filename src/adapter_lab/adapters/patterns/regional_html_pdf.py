from __future__ import annotations

from pathlib import Path

from adapter_lab.adapters.patterns.catalog_html import CatalogHtmlAdapter
from adapter_lab.core.models import EvidenceAsset, ExtractionResult, FetchRecord, RawCandidate
from adapter_lab.utils.urls import is_pdf_url


class RegionalHtmlPdfAdapter(CatalogHtmlAdapter):
    """Adapter for regional portals with HTML detail pages and linked PDFs."""

    def fetch(self, candidate: RawCandidate) -> tuple[FetchRecord, list[EvidenceAsset]]:
        record, body = self.http_fetcher.fetch(
            candidate.url,
            source_id=self.source_def.id,
            candidate_id=candidate.id,
        )
        main_asset = self._asset_from_fetch(record, candidate.url, body)
        assets = [main_asset]
        html = body.decode("utf-8", errors="ignore")
        links = self.html_extractor.extract_links(html, candidate.url)
        pdf_links = [link for link in links if is_pdf_url(link)]
        if pdf_links:
            assets.extend(
                self._download_linked_assets(html, candidate.url, parent_asset_id=main_asset.id)
            )
        record.asset_ids = [asset.id for asset in assets]
        return record, assets

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        html_asset = next((asset for asset in assets if asset.asset_type.value == "html"), None)
        pdf_assets = [asset for asset in assets if asset.asset_type.value == "pdf"]
        html_text = ""
        title = None
        if html_asset:
            html = Path(html_asset.local_path).read_text(encoding="utf-8", errors="ignore")
            title = self.html_extractor.extract_title(html)
            html_text = self.html_extractor.extract_text(html)
        pdf_text = "\n".join(self._read_asset_text(asset) for asset in pdf_assets)
        combined_text = "\n".join(part for part in [html_text, pdf_text] if part)
        notes = []
        if not pdf_assets:
            notes.append("No linked PDF detected on detail page.")
        return self._build_result(
            candidate_id="",
            combined_text=combined_text,
            attachment_urls=[asset.original_url for asset in pdf_assets],
            title=title,
            notes=notes,
            raw_fields={"html_present": bool(html_asset), "pdf_count": len(pdf_assets)},
        )
