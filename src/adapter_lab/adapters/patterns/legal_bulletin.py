from __future__ import annotations

from pathlib import Path

from adapter_lab.adapters.patterns.regional_html_pdf import RegionalHtmlPdfAdapter
from adapter_lab.core.models import EvidenceAsset, ExtractionResult, RawCandidate


class LegalBulletinAdapter(RegionalHtmlPdfAdapter):
    """Adapter for legal bulletin or gazette-style sources."""

    def discover(self) -> list[RawCandidate]:
        candidates = super().discover()
        bulletin_candidates = [
            candidate
            for candidate in candidates
            if any(token in candidate.url.lower() for token in ("bur", "bollettino", "gazzetta", "bando"))
        ]
        return bulletin_candidates or candidates

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        result = super().extract(assets)
        html_asset = next((asset for asset in assets if asset.asset_type.value == "html"), None)
        if html_asset:
            html = Path(html_asset.local_path).read_text(encoding="utf-8", errors="ignore")
            if "bollettino" in html.lower() or "gazzetta" in html.lower():
                result.extraction_notes.append("Bulletin-style source detected from HTML evidence.")
        return result
