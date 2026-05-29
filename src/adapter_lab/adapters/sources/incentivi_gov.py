from __future__ import annotations

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from adapter_lab.adapters.patterns.catalog_html import CatalogHtmlAdapter
from adapter_lab.core.models import RawCandidate, SourceDefinition
from adapter_lab.core.registry import register_adapter
from adapter_lab.core.types import AdapterStatus, SourceType
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import normalize_url


@register_adapter("incentivi_gov")
class IncentiviGovAdapter(CatalogHtmlAdapter):
    """Source adapter for incentivi.gov.it catalog pages."""

    source_def = SourceDefinition(
        id="incentivi_gov",
        name="Incentivi.gov.it",
        base_url="https://www.incentivi.gov.it",
        source_type=SourceType.CATALOG_HTML,
        start_urls=["https://www.incentivi.gov.it/it/catalogo"],
        tags=["italia", "nazionale", "catalogo"],
        notes="Selectors are simplified for lab prototyping. Review live structure before production promotion.",
        adapter_status=AdapterStatus.DRAFT,
    )

    def discover(self) -> list[RawCandidate]:
        listing_url = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(listing_url, source_id=self.source_def.id)
        soup = BeautifulSoup(body.decode("utf-8", errors="ignore"), "lxml")
        candidates: list[RawCandidate] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = normalize_url(anchor.get("href", ""), listing_url)
            label = anchor.get_text(" ", strip=True)
            if not href or href in seen:
                continue
            if "/it/" in href and any(
                token in href.lower() for token in ("incentivo", "bando", "misura", "agevolazione")
            ):
                seen.add(href)
                candidates.append(
                    RawCandidate(
                        id=short_id(href),
                        source_id=self.source_def.id,
                        url=href,
                        discovered_at=datetime.now(UTC),
                        title=label or None,
                        metadata={"listing_url": listing_url},
                    )
                )
        return candidates or super().discover()
