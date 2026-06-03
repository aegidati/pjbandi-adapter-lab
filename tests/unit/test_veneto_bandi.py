from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.sources.veneto_bandi import VenetoBandiAdapter
from adapter_lab.core.models import EvidenceAsset, FetchRecord, RawCandidate
from adapter_lab.core.types import AssetType, ExtractionStatus, SourceType
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import hash_content, short_id

FIXTURES = Path("tests/fixtures/veneto_bandi")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_fetcher(listing_html: bytes, detail_html: bytes):
    """Return a monkeypatch target that serves fixture HTML."""

    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "veneto_bandi",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        is_listing = "Elenco" in url
        body = listing_html if is_listing else detail_html
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

    return fake_fetch


# ---------------------------------------------------------------------------
# Adapter registration
# ---------------------------------------------------------------------------


def test_veneto_bandi_adapter_is_registered() -> None:
    """Adapter importabile con source definition corretta."""
    from adapter_lab.adapters.sources import load_source_adapters
    from adapter_lab.core.registry import REGISTRY

    load_source_adapters()
    adapter_cls = REGISTRY.get("veneto_bandi")
    assert adapter_cls is VenetoBandiAdapter


def test_veneto_bandi_source_definition() -> None:
    adapter = VenetoBandiAdapter()
    sd = adapter.source_def
    assert sd.id == "veneto_bandi"
    assert sd.source_type == SourceType.REGIONAL_HTML_PDF
    assert any("Index" in url for url in sd.start_urls)
    assert any("Elenco" in url for url in sd.start_urls)
    assert "veneto" in sd.tags


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_veneto_bandi_discover_returns_detail_candidates(monkeypatch) -> None:
    listing_html = (FIXTURES / "listing.html").read_bytes()
    detail_html = (FIXTURES / "detail.html").read_bytes()

    monkeypatch.setattr(
        HttpFetcher, "fetch", _make_fake_fetcher(listing_html, detail_html)
    )

    adapter = VenetoBandiAdapter()
    candidates = adapter.discover()

    assert len(candidates) >= 3
    urls = [c.url for c in candidates]
    assert all("bandi.regione.veneto.it" in u for u in urls)
    detail_tokens = ("dettaglio", "bando", "scheda", "avviso")
    assert all(any(token in u.lower() for token in detail_tokens) for u in urls)


def test_veneto_bandi_discover_deduplicates_candidates(monkeypatch) -> None:
    """Href ripetuti non devono produrre candidati duplicati."""
    duplicate_html = (
        b"<html><body>"
        b'<a href="/Public/Dettaglio/BandoPMI2025">Bando A</a>'
        b'<a href="/Public/Dettaglio/BandoPMI2025">Bando A (copia)</a>'
        b'<a href="/Public/Dettaglio/AvvisoB">Bando B</a>'
        b"</body></html>"
    )
    detail_html = (FIXTURES / "detail.html").read_bytes()

    monkeypatch.setattr(
        HttpFetcher, "fetch", _make_fake_fetcher(duplicate_html, detail_html)
    )

    adapter = VenetoBandiAdapter()
    candidates = adapter.discover()

    urls = [c.url for c in candidates]
    assert len(urls) == len(set(urls)), "Duplicate URLs must be deduplicated"
    assert len(candidates) == 2


def test_veneto_bandi_discover_metadata_includes_region(monkeypatch) -> None:
    listing_html = (FIXTURES / "listing.html").read_bytes()
    detail_html = (FIXTURES / "detail.html").read_bytes()

    monkeypatch.setattr(
        HttpFetcher, "fetch", _make_fake_fetcher(listing_html, detail_html)
    )

    adapter = VenetoBandiAdapter()
    candidates = adapter.discover()

    for candidate in candidates:
        assert candidate.metadata.get("region") == "veneto"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _make_html_asset(html_bytes: bytes, tmp_path: Path) -> EvidenceAsset:
    path = tmp_path / "detail.html"
    path.write_bytes(html_bytes)
    return EvidenceAsset(
        id="asset-html-1",
        source_id="veneto_bandi",
        fetch_record_id="fetch-1",
        asset_type=AssetType.HTML,
        mime_type="text/html",
        original_url=("https://bandi.regione.veneto.it/Public/Dettaglio/BandoPMI2025"),
        local_path=str(path),
        hash=hash_content(html_bytes),
        file_size=len(html_bytes),
    )


def test_veneto_bandi_extract_title_from_html(tmp_path) -> None:
    detail_html = (FIXTURES / "detail.html").read_bytes()
    asset = _make_html_asset(detail_html, tmp_path)

    adapter = VenetoBandiAdapter()
    result = adapter.extract([asset])

    assert result.title is not None
    assert "Transizione Digitale" in result.title or "PMI" in result.title


def test_veneto_bandi_extract_deadline_from_html(tmp_path) -> None:
    detail_html = (FIXTURES / "detail.html").read_bytes()
    asset = _make_html_asset(detail_html, tmp_path)

    adapter = VenetoBandiAdapter()
    result = adapter.extract([asset])

    assert result.deadline is not None
    assert "2025" in result.deadline


def test_veneto_bandi_extract_notes_include_veneto_branding(tmp_path) -> None:
    detail_html = (FIXTURES / "detail.html").read_bytes()
    asset = _make_html_asset(detail_html, tmp_path)

    adapter = VenetoBandiAdapter()
    result = adapter.extract([asset])

    assert any("Veneto" in note for note in result.extraction_notes)


def test_veneto_bandi_extract_authority_from_css_class(tmp_path) -> None:
    html_with_authority = (
        b"<html><body>"
        b"<h1>Bando Test Veneto</h1>"
        b'<p class="ente-emittente">Regione del Veneto '
        b"\xe2\x80\x93 Direzione Industria</p>"
        b"<p>Scadenza: 30/06/2025</p>"
        b"</body></html>"
    )
    asset = _make_html_asset(html_with_authority, tmp_path)

    adapter = VenetoBandiAdapter()
    result = adapter.extract([asset])

    assert "authority" in result.raw_fields
    assert "Veneto" in result.raw_fields["authority"]


def test_veneto_bandi_extract_title_ignores_hidden_portal_h1(tmp_path) -> None:
    html = b"""<!DOCTYPE html>
<html><head><title>Dettaglio Avviso n. 123 - Bandi</title></head><body>
    <h1 style="display: none;">
        Portale Bandi Avvisi Concorsi - Regione del Veneto
    </h1>
  <div class="rowContainer">
    <div class="display-label">Titolo</div>
    <div class="display-field">Bando specifico energia 2026</div>
  </div>
  <div class="rowContainer">
    <div class="display-label">Scadenza:</div>
    <div class="display-field">30/06/2026 13:00</div>
  </div>
</body></html>"""
    asset = _make_html_asset(html, tmp_path)

    adapter = VenetoBandiAdapter()
    result = adapter.extract([asset])

    assert result.title == "Bando specifico energia 2026"


def test_veneto_bandi_fetch_collects_download_attachments(
    monkeypatch, tmp_path
) -> None:
    listing_html = (FIXTURES / "listing.html").read_bytes()
    detail_html = b"""<!DOCTYPE html>
<html><body>
  <a href="/Public/Download?idAllegato=111">Allegato A</a>
  <a href="/Public/Download?idAllegato=222">Allegato B</a>
</body></html>"""

    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "veneto_bandi",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        if "idAllegato=" in url:
            body = b"%PDF-1.7 fake-pdf"
            content_type = "application/pdf"
        elif "Elenco" in url:
            body = listing_html
            content_type = "text/html"
        else:
            body = detail_html
            content_type = "text/html"
        path = tmp_path / f"{short_id(url)}.bin"
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
    adapter = VenetoBandiAdapter()
    candidate = RawCandidate(
        id="cand-1",
        source_id="veneto_bandi",
        url="https://bandi.regione.veneto.it/Public/Dettaglio?idAtto=123",
    )

    _, assets = adapter.fetch(candidate)
    attachment_urls = [
        asset.original_url for asset in assets if asset.asset_type != AssetType.HTML
    ]

    assert len(attachment_urls) == 2
    assert all("/Public/Download?idAllegato=" in url for url in attachment_urls)


def test_veneto_bandi_extract_deadline_not_filled_by_generic_fallback(
    tmp_path,
) -> None:
    html = b"""<!DOCTYPE html>
<html><body>
    <h1 style="display: none;">
        Portale Bandi Avvisi Concorsi - Regione del Veneto
    </h1>
  <p>SCADENZARIO</p>
  <p>Pubblicazione: 20/05/2026</p>
  <div class="rowContainer">
    <div class="display-label">Titolo</div>
    <div class="display-field">Avviso senza scadenza esplicita</div>
  </div>
</body></html>"""
    asset = _make_html_asset(html, tmp_path)

    adapter = VenetoBandiAdapter()
    result = adapter.extract([asset])

    assert result.deadline is None
    assert result.status == ExtractionStatus.PARTIAL
