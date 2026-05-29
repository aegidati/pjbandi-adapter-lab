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

# Tokens that signal a URL leads to a bando detail page on this portal.
_DETAIL_TOKENS = ("dettaglio", "bando", "scheda", "avviso")


@register_adapter("veneto_bandi")
class VenetoBandiAdapter(RegionalHtmlPdfAdapter):
    """Source adapter for bandi.regione.veneto.it.

    Entry point: /Public/Index (portal home).
    Listing page: /Public/Elenco (all open and recent calls).
    Detail pages: identified by URL tokens such as 'Dettaglio' or 'Scheda'.

    Assumptions:
    - Detail page URLs contain at least one of: dettaglio, bando, scheda, avviso.
    - PDF attachments are linked from each detail page.
    - Pagination URL pattern is unknown and not yet handled; limit discovery to
      the first listing page until the pattern is confirmed with a live fixture.
    """

    # The listing URL is kept explicit so discover() does not depend on
    # start_urls ordering and the entry point can be documented separately.
    _LISTING_URL = "https://bandi.regione.veneto.it/Public/Elenco"

    source_def = SourceDefinition(
        id="veneto_bandi",
        name="Bandi Regione Veneto",
        base_url="https://bandi.regione.veneto.it",
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
            "Pagination structure unverified; promote to STABLE after live fixture validation."
        ),
        adapter_status=AdapterStatus.TESTING,
    )

    def discover(self) -> list[RawCandidate]:
        """Discover bando detail URLs from the Veneto portal listing page."""
        listing_url = self._LISTING_URL
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = normalize_url(anchor.get("href", ""), listing_url)
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
                        metadata={"listing_url": listing_url, "region": "veneto"},
                    )
                )
        return candidates or super().discover()

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        """Extract structured fields from fetched Veneto bando evidence assets."""
        result = super().extract(assets)
        html_asset = next((asset for asset in assets if asset.asset_type.value == "html"), None)
        if html_asset:
            html = Path(html_asset.local_path).read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            # Try to capture the emitting authority when marked in the portal HTML.
            authority_node = soup.select_one(
                ".ente-emittente, .autorita, [class*='ente'], [class*='autorita']"
            )
            if authority_node:
                result.raw_fields["authority"] = authority_node.get_text(" ", strip=True)
            if "veneto" in html.lower():
                result.extraction_notes.append(
                    "Detected Veneto-specific branding in HTML evidence."
                )
        return result
