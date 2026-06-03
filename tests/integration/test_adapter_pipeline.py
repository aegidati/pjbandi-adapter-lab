from __future__ import annotations

from typing import cast
from datetime import UTC, datetime
from pathlib import Path

from pydantic import HttpUrl

from adapter_lab.adapters.patterns.catalog_html import CatalogHtmlAdapter
from adapter_lab.adapters.sources.incentivi_gov import IncentiviGovAdapter
from adapter_lab.core.models import FetchRecord, SourceDefinition
from adapter_lab.core.types import SourceType
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import hash_content


class FixtureCatalogAdapter(CatalogHtmlAdapter):
    source_def = SourceDefinition(
        id="fixture_catalog",
        name="Fixture Catalog",
        base_url=cast(HttpUrl, "https://fixtures.example.com"),
        source_type=SourceType.CATALOG_HTML,
        start_urls=["https://fixtures.example.com/listing"],
        tags=["fixture"],
    )


def test_catalog_html_adapter_discover_from_fixture(monkeypatch) -> None:
    fixture_html = Path("tests/fixtures/sample_listing.html").read_bytes()
    detail_html = b"<html><body><h1>Bando transizione digitale</h1><p>Scadenza 15/01/2025</p></body></html>"

    def fake_fetch(
        self,
        url: str,
        source_id: str = "generic",
        candidate_id: str | None = None,
    ):
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
        candidate.url.startswith("https://fixtures.example.com/")
        for candidate in candidates
    )


def test_incentivi_gov_adapter_pipeline_from_solr_fixture(monkeypatch) -> None:
    listing_html = b"""<!DOCTYPE html>
<html><head>
<script id="service-config" type="application/json">
[
    {"id": "solrQueryLimit", "value": "50"},
    {"id": "solrEndpoint", "value": "/solr/coredrupal/select"}
]
</script>
</head><body></body></html>"""
    solr_json = b"""{
    "response": {
        "docs": [
            {
                "id": "doc-1",
                "title": "Incentivo test integrazione",
                "url": "/it/catalogo/incentivo-test-integrazione",
                "data_pubblicazione": "01/06/2026",
                "scadenza": "30/06/2026"
            }
        ]
    }
}"""
    detail_html = (
        b"<html><body><h1>Titolo dettaglio</h1><p>Scadenza 31/12/2026</p></body></html>"
    )

    def fake_fetch(
        self,
        url: str,
        source_id: str = "generic",
        candidate_id: str | None = None,
    ):
        if "/solr/coredrupal/select" in url:
            body = solr_json
            content_type = "application/json"
        elif url.endswith("/it/catalogo"):
            body = listing_html
            content_type = "text/html"
        else:
            body = detail_html
            content_type = "text/html"
        path = Path(
            f"data/raw/{source_id}/{candidate_id or 'listing'}_{hash_content(url.encode())[:8]}.bin"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        record = FetchRecord(
            id=candidate_id or hash_content(url.encode())[:12],
            candidate_id=candidate_id or "listing",
            source_id=source_id,
            original_url=url,
            final_url=url,
            fetched_at=datetime.now(UTC),
            status_code=200,
            content_type=content_type,
            body_hash=hash_content(body),
            local_path=str(path),
        )
        return record, body

    monkeypatch.setattr(HttpFetcher, "fetch", fake_fetch)

    adapter = IncentiviGovAdapter()
    results = adapter.run_pipeline(limit=1)

    assert len(results) == 1
    assert results[0].title == "Incentivo test integrazione"
    assert results[0].publication_date == "2026-06-01"
    assert results[0].deadline == "2026-06-30"
