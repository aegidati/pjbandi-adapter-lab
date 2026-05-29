from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.patterns.catalog_html import CatalogHtmlAdapter
from adapter_lab.core.models import FetchRecord, SourceDefinition
from adapter_lab.core.types import SourceType
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import hash_content


class FixtureCatalogAdapter(CatalogHtmlAdapter):
    source_def = SourceDefinition(
        id="fixture_catalog",
        name="Fixture Catalog",
        base_url="https://fixtures.example.com",
        source_type=SourceType.CATALOG_HTML,
        start_urls=["https://fixtures.example.com/listing"],
        tags=["fixture"],
    )


def test_catalog_html_adapter_discover_from_fixture(monkeypatch) -> None:
    fixture_html = Path("tests/fixtures/sample_listing.html").read_bytes()
    detail_html = (
        b"<html><body><h1>Bando transizione digitale</h1><p>Scadenza 15/01/2025</p></body></html>"
    )

    def fake_fetch(self, url: str, source_id: str = "generic", candidate_id: str | None = None):
        body = fixture_html if url.endswith("/listing") else detail_html
        path = Path(f"data/raw/{source_id}/{candidate_id or 'listing'}.html")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        record = FetchRecord(
            id=candidate_id or "listing",
            candidate_id=candidate_id or "listing",
            source_id=source_id,
            original_url=url,
            final_url=url,
            fetched_at=datetime.now(UTC),
            status_code=200,
            content_type="text/html",
            body_hash=hash_content(body),
            local_path=str(path),
        )
        return record, body

    monkeypatch.setattr(HttpFetcher, "fetch", fake_fetch)
    adapter = FixtureCatalogAdapter()
    candidates = adapter.discover()
    assert len(candidates) >= 3
    assert all(
        candidate.url.startswith("https://fixtures.example.com/") for candidate in candidates
    )
