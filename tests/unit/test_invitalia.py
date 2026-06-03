from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.sources.invitalia import InvitaliaAdapter
from adapter_lab.core.models import EvidenceAsset, FetchRecord
from adapter_lab.core.types import AssetType, SourceType
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import hash_content, short_id

FIXTURES = Path("tests/fixtures/invitalia")


def _make_fake_fetcher(listing_page0: bytes, listing_page1: bytes, detail_html: bytes):
    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "invitalia",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        if "page=1" in url:
            body = listing_page1
            content_type = "text/html"
        elif "/incentivi-e-strumenti/" in url:
            body = detail_html
            content_type = "text/html"
        else:
            body = listing_page0
            content_type = "text/html"

        path = Path(f"data/raw/{source_id}/{short_id(url)}.html")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        record = FetchRecord(
            id=short_id(f"rec:{url}"),
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

    return fake_fetch


def _make_html_asset(html_bytes: bytes, tmp_path: Path) -> EvidenceAsset:
    path = tmp_path / "invitalia-detail.html"
    path.write_bytes(html_bytes)
    return EvidenceAsset(
        id="asset-html-1",
        source_id="invitalia",
        fetch_record_id="fetch-1",
        asset_type=AssetType.HTML,
        mime_type="text/html",
        original_url=(
            "https://www.invitalia.it/incentivi-e-strumenti/"
            "voucher-il-sostegno-dei-piccoli-editori"
        ),
        local_path=str(path),
        hash=hash_content(html_bytes),
        file_size=len(html_bytes),
    )


def test_invitalia_adapter_is_registered() -> None:
    from adapter_lab.adapters.sources import load_source_adapters
    from adapter_lab.core.registry import REGISTRY

    load_source_adapters()
    adapter_cls = REGISTRY.get("invitalia")
    assert adapter_cls is InvitaliaAdapter


def test_invitalia_source_definition() -> None:
    adapter = InvitaliaAdapter()
    sd = adapter.source_def
    assert sd.id == "invitalia"
    assert sd.source_type == SourceType.CATALOG_HTML
    assert sd.start_urls == [
        "https://www.invitalia.it/per-le-imprese/incentivi-e-strumenti"
    ]


def test_invitalia_discover_paginates_and_deduplicates(monkeypatch) -> None:
    listing_page0 = (FIXTURES / "listing_page0.html").read_bytes()
    listing_page1 = (FIXTURES / "listing_page1.html").read_bytes()
    detail_html = (FIXTURES / "detail.html").read_bytes()

    monkeypatch.setattr(
        HttpFetcher,
        "fetch",
        _make_fake_fetcher(listing_page0, listing_page1, detail_html),
    )

    adapter = InvitaliaAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 3
    urls = [candidate.url for candidate in candidates]
    assert len(urls) == len(set(urls))
    assert all(
        url.startswith("https://www.invitalia.it/incentivi-e-strumenti/")
        for url in urls
    )
    assert all("from=" not in url for url in urls)
    assert any(candidate.metadata.get("page") == 1 for candidate in candidates)


def test_invitalia_extract_dates_from_labeled_fields(tmp_path) -> None:
    detail_html = (FIXTURES / "detail.html").read_bytes()
    asset = _make_html_asset(detail_html, tmp_path)

    adapter = InvitaliaAdapter()
    result = adapter.extract([asset])

    assert result.title == "Voucher per il sostegno dei piccoli editori"
    assert result.publication_date == "2026-06-22"
    assert result.deadline == "2026-09-30"
    assert result.status.value == "success"


def test_invitalia_discover_prefers_direct_api_when_available(monkeypatch) -> None:
    listing_html = b"""<!DOCTYPE html>
<html><body>
    <script>
        window.__config = {"endpoint": "/api/incentivi"};
    </script>
</body></html>"""
    api_payload = b"""{
    "items": [
        {
            "url": "/incentivi-e-strumenti/test-incentivo",
            "title": "LEGGI TUTTO SU TEST INCENTIVO ATTIVO"
        }
    ]
}"""

    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "invitalia",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        body = api_payload if "/api/incentivi" in url else listing_html
        content_type = "application/json" if "/api/incentivi" in url else "text/html"
        path = Path(f"data/raw/{source_id}/{short_id(url)}.bin")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        record = FetchRecord(
            id=short_id(f"rec:{url}"),
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

    adapter = InvitaliaAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 1
    assert candidates[0].url.endswith("/incentivi-e-strumenti/test-incentivo")
    assert candidates[0].title == "TEST INCENTIVO"
    assert candidates[0].metadata.get("discovery_mode") == "direct_api"


def test_invitalia_discover_cleans_noisy_html_titles(monkeypatch) -> None:
    listing_html = b"""<!DOCTYPE html>
<html><body>
    <a href="/incentivi-e-strumenti/caso-titolo">LEGGI TUTTO SU CASO TITOLO ATTIVO</a>
</body></html>"""
    detail_html = (FIXTURES / "detail.html").read_bytes()

    monkeypatch.setattr(
        HttpFetcher,
        "fetch",
        _make_fake_fetcher(listing_html, b"<html><body></body></html>", detail_html),
    )

    adapter = InvitaliaAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 1
    assert candidates[0].title == "CASO TITOLO"
