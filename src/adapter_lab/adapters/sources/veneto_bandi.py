from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from adapter_lab.adapters.patterns.regional_html_pdf import RegionalHtmlPdfAdapter
from adapter_lab.core.models import EvidenceAsset, ExtractionResult, RawCandidate, SourceDefinition
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import AdapterStatus, SourceType
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import normalize_url


@register_adapter("veneto_bandi")
class VenetoBandiAdapter(RegionalHtmlPdfAdapter):
    """Source adapter for bandi.regione.veneto.it."""

    source_def = SourceDefinition(
        id="veneto_bandi",
        name="Bandi Regione Veneto",
        base_url="https://bandi.regione.veneto.it",
        source_type=SourceType.REGIONAL_HTML_PDF,
        start_urls=["https://bandi.regione.veneto.it/Public/Elenco"],
        tags=["veneto", "regione", "bandi"],
        notes="Specific extraction rules can be promoted once selectors are validated with fixtures.",
        adapter_status=AdapterStatus.TESTING,
    )

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")
        candidates: list[RawCandidate] = []
        for anchor in soup.select("a[href]"):
            href = normalize_url(anchor.get("href", ""), listing_url)
            label = anchor.get_text(" ", strip=True)
            if any(token in href.lower() for token in ("dettaglio", "bando", "scheda", "avviso")):
                candidates.append(
                    RawCandidate(
                        id=short_id(href),
                        source_id=self.source_def.id,
                        url=href,
                        discovered_at=datetime.now(UTC),
                        title=label or None,
                        metadata={"listing_url": listing_url, "region": "veneto"},
                    )
                )
        return candidates or super().discover()

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        result = super().extract(assets)
        html_asset = next((asset for asset in assets if asset.asset_type.value == "html"), None)
        if html_asset:
            html = Path(html_asset.local_path).read_text(encoding="utf-8", errors="ignore")
            if "veneto" in html.lower():
                result.extraction_notes.append(
                    "Detected Veneto-specific branding in HTML evidence."
                )
        return result
