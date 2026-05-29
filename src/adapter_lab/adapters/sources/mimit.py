from __future__ import annotations

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from adapter_lab.adapters.patterns.regional_html_pdf import RegionalHtmlPdfAdapter
from adapter_lab.core.models import RawCandidate, SourceDefinition
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import AdapterStatus, SourceType
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import normalize_url


@register_adapter("mimit")
class MimitAdapter(RegionalHtmlPdfAdapter):
    """Source adapter for MIMIT funding and incentive pages."""

    source_def = SourceDefinition(
        id="mimit",
        name="Ministero delle Imprese e del Made in Italy",
        base_url="https://www.mimit.gov.it",
        source_type=SourceType.REGIONAL_HTML_PDF,
        start_urls=["https://www.mimit.gov.it/it/incentivi"],
        tags=["ministero", "italia", "incentivi"],
        notes="Specific selectors should be reviewed against representative MIMIT fixtures.",
        adapter_status=AdapterStatus.DRAFT,
    )

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")
        candidates: list[RawCandidate] = []
        for anchor in soup.select("a[href]"):
            href = normalize_url(anchor.get("href", ""), listing_url)
            if any(token in href.lower() for token in ("bando", "incentivi", "agevolazioni", "decreto")):
                candidates.append(
                    RawCandidate(
                        id=short_id(href),
                        source_id=self.source_def.id,
                        url=href,
                        discovered_at=datetime.now(UTC),
                        title=anchor.get_text(" ", strip=True) or None,
                        metadata={"listing_url": listing_url},
                    )
                )
        return candidates or super().discover()
