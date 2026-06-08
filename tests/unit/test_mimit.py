from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.sources.mimit import MimitAdapter
from adapter_lab.core.models import EvidenceAsset, FetchRecord
from adapter_lab.core.types import AssetType, SourceType
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import hash_content, short_id

FIXTURES = Path("tests/fixtures/mimit")


def _make_fake_fetcher(listing_page0: bytes, listing_page1: bytes, detail_html: bytes):
    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "mimit",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        if "start=20" in url:
            body = listing_page1
            content_type = "text/html"
        elif "/it/incentivi/" in url:
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
    path = tmp_path / "mimit-detail.html"
    path.write_bytes(html_bytes)
    return EvidenceAsset(
        id="asset-html-mimit-1",
        source_id="mimit",
        fetch_record_id="fetch-1",
        asset_type=AssetType.HTML,
        mime_type="text/html",
        original_url="https://www.mimit.gov.it/it/incentivi/fondo-straordinario-editoria-2025",
        local_path=str(path),
        hash=hash_content(html_bytes),
        file_size=len(html_bytes),
    )


def test_mimit_adapter_is_registered() -> None:
    from adapter_lab.adapters.sources import load_source_adapters
    from adapter_lab.core.registry import REGISTRY

    load_source_adapters()
    adapter_cls = REGISTRY.get("mimit")
    assert adapter_cls is MimitAdapter


def test_mimit_source_definition() -> None:
    adapter = MimitAdapter()
    sd = adapter.source_def
    assert sd.id == "mimit"
    assert sd.source_type == SourceType.REGIONAL_HTML_PDF
    assert sd.start_urls == ["https://www.mimit.gov.it/it/incentivi"]


def test_mimit_discover_paginates_and_filters(monkeypatch) -> None:
    listing_page0 = (FIXTURES / "listing_page0.html").read_bytes()
    listing_page1 = (FIXTURES / "listing_page1.html").read_bytes()
    detail_html = (FIXTURES / "detail.html").read_bytes()

    monkeypatch.setattr(
        HttpFetcher,
        "fetch",
        _make_fake_fetcher(listing_page0, listing_page1, detail_html),
    )

    adapter = MimitAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 3
    urls = [candidate.url for candidate in candidates]
    assert len(urls) == len(set(urls))
    assert all(url.startswith("https://www.mimit.gov.it/it/incentivi/") for url in urls)
    assert any(candidate.metadata.get("page_start") == 20 for candidate in candidates)


def test_mimit_extract_reads_title_and_dates(tmp_path) -> None:
    detail_html = (FIXTURES / "detail.html").read_bytes()
    asset = _make_html_asset(detail_html, tmp_path)

    adapter = MimitAdapter()
    result = adapter.extract([asset])

    assert result.title == "Fondo straordinario editoria 2025"
    assert result.publication_date == "2026-06-03"
    assert result.deadline == "2026-09-30"
    assert result.status.value == "success"


def test_mimit_discover_filters_non_detail_section_urls(monkeypatch) -> None:
    listing_html = b"""<!DOCTYPE html>
<html><body>
    <a href="/it/incentivi/faq">FAQ</a>
    <a href="/it/incentivi/open-data">Open Data</a>
    <a href="/it/incentivi/fondo-straordinario-editoria-2025">Fondo Editoria</a>
</body></html>"""

    monkeypatch.setattr(
        HttpFetcher,
        "fetch",
        _make_fake_fetcher(listing_html, b"<html><body></body></html>", b"<html></html>"),
    )

    adapter = MimitAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 1
    assert candidates[0].url.endswith(
        "/it/incentivi/fondo-straordinario-editoria-2025"
    )
