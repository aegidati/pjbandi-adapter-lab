from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.sources.incentivi_gov import IncentiviGovAdapter
from adapter_lab.core.models import EvidenceAsset, FetchRecord, RawCandidate
from adapter_lab.core.types import AssetType, ExtractionStatus
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import hash_content, short_id


def _fake_fetch_with_solr_docs(
    solr_docs: list[Mapping[str, object]],
    *,
    rows_in_config: str = "50",
):
    listing_html = b"""<!DOCTYPE html>
<html><head>
<script id="service-config" type="application/json">
[
    {"id": "solrQueryLimit", "value": "__ROWS__"},
  {"id": "solrEndpoint", "value": "/solr/coredrupal/select"}
]
</script>
</head><body>
  <a href="/it/privacy">Privacy</a>
</body></html>""".replace(b"__ROWS__", rows_in_config.encode("utf-8"))

    payload = {"response": {"docs": solr_docs}}
    solr_body = json.dumps(payload).encode("utf-8")

    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "incentivi_gov",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        is_solr = "/solr/coredrupal/select" in url
        body = solr_body if is_solr else listing_html
        content_type = "application/json" if is_solr else "text/html"
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

    return fake_fetch


def test_incentivi_gov_discover_uses_solr_docs(monkeypatch) -> None:
    docs: list[dict[str, object]] = [
        {
            "id": "inc-001",
            "title": "Incentivo Transizione Digitale",
            "url": "/it/catalogo/incentivo-transizione-digitale",
        },
        {
            "id": "inc-002",
            "name": "Misura Green PMI",
            "link": "https://www.incentivi.gov.it/it/incentivi/misura-green-pmi",
        },
    ]
    monkeypatch.setattr(HttpFetcher, "fetch", _fake_fetch_with_solr_docs(docs))

    adapter = IncentiviGovAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 2
    assert candidates[0].title == "Incentivo Transizione Digitale"
    assert candidates[1].title == "Misura Green PMI"
    assert all(
        candidate.url.startswith("https://www.incentivi.gov.it/it/")
        for candidate in candidates
    )
    assert all("solr_url" in candidate.metadata for candidate in candidates)


def test_incentivi_gov_discover_filters_non_detail_paths(monkeypatch) -> None:
    docs: list[dict[str, object]] = [
        {"id": "bad-1", "title": "Privacy", "url": "/it/privacy"},
        {"id": "bad-2", "title": "FAQ", "url": "/it/faq"},
        {
            "id": "ok-1",
            "title": "Incentivo Export",
            "url": "/it/catalogo/incentivo-export",
        },
    ]
    monkeypatch.setattr(HttpFetcher, "fetch", _fake_fetch_with_solr_docs(docs))

    adapter = IncentiviGovAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 1
    assert candidates[0].url.endswith("/it/catalogo/incentivo-export")


def test_incentivi_gov_discover_caps_solr_rows(monkeypatch) -> None:
    docs: list[dict[str, object]] = [
        {
            "id": "inc-001",
            "title": "Incentivo Test Cap",
            "url": "/it/catalogo/incentivo-test-cap",
        }
    ]
    monkeypatch.setattr(
        HttpFetcher,
        "fetch",
        _fake_fetch_with_solr_docs(docs, rows_in_config="8000"),
    )

    adapter = IncentiviGovAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 1
    assert "rows=300" in candidates[0].metadata.get("solr_url", "")


def test_incentivi_gov_discover_static_fallback_when_solr_invalid(
    monkeypatch,
) -> None:
    listing_html = b"""<!DOCTYPE html>
<html><head>
<script id="service-config" type="application/json">
[
  {"id": "solrEndpoint", "value": "/solr/coredrupal/select"}
]
</script>
</head><body>
  <a href="/it/privacy">Privacy</a>
  <a href="/it/catalogo/incentivo-fallback">Incentivo Fallback</a>
</body></html>"""

    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "incentivi_gov",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        is_solr = "/solr/coredrupal/select" in url
        body = b"not-json" if is_solr else listing_html
        content_type = "application/json" if is_solr else "text/html"
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

    adapter = IncentiviGovAdapter()
    candidates = adapter.discover()

    assert len(candidates) == 1
    assert candidates[0].url.endswith("/it/catalogo/incentivo-fallback")
    assert candidates[0].metadata.get("discovery_mode") == "static_fallback"


def test_incentivi_gov_fetch_adds_solr_json_asset(monkeypatch, tmp_path) -> None:
    detail_html = b"<html><body><h1>Dettaglio incentivo</h1></body></html>"

    def fake_fetch(
        self: HttpFetcher,
        url: str,
        source_id: str = "incentivi_gov",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        body = detail_html
        path = tmp_path / f"{short_id(url)}.html"
        path.write_bytes(body)
        record = FetchRecord(
            id=short_id(f"rec:{url}"),
            candidate_id=candidate_id or "candidate",
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

    adapter = IncentiviGovAdapter()
    candidate = RawCandidate(
        id="cand-1",
        source_id="incentivi_gov",
        url="https://www.incentivi.gov.it/it/catalogo/incentivo-test",
        title="Titolo da Solr",
        metadata={
            "solr_url": "https://www.incentivi.gov.it/solr/coredrupal/select?q=*:*",
            "solr_doc": {
                "id": "doc-1",
                "title": "Titolo da Solr",
                "data_scadenza": "2026-12-31",
            },
        },
    )

    _, assets = adapter.fetch(candidate)
    json_assets = [asset for asset in assets if asset.asset_type == AssetType.JSON]

    assert len(json_assets) == 1
    payload = json.loads(Path(json_assets[0].local_path).read_text(encoding="utf-8"))
    assert payload["id"] == "doc-1"


def test_incentivi_gov_extract_prefers_solr_fields(tmp_path) -> None:
    adapter = IncentiviGovAdapter()
    html_path = tmp_path / "detail.html"
    html_path.write_text(
        "<html><body><h1>Titolo HTML</h1><p>Scadenza 10/01/2027</p></body></html>",
        encoding="utf-8",
    )
    json_path = tmp_path / "solr_doc.json"
    json_path.write_text(
        json.dumps(
            {
                "id": "doc-99",
                "title": "Titolo Solr Finale",
                "data_pubblicazione": "03/06/2026",
                "deadline": "2026-12-15",
                "attachments": ["/files/allegato-a.pdf"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assets = [
        EvidenceAsset(
            id="asset-html",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.HTML,
            mime_type="text/html",
            original_url="https://www.incentivi.gov.it/it/catalogo/incentivo-test",
            local_path=str(html_path),
            hash=hash_content(html_path.read_bytes()),
            file_size=html_path.stat().st_size,
        ),
        EvidenceAsset(
            id="asset-json",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.JSON,
            mime_type="application/json",
            original_url="https://www.incentivi.gov.it/solr/coredrupal/select",
            local_path=str(json_path),
            hash=hash_content(json_path.read_bytes()),
            file_size=json_path.stat().st_size,
        ),
    ]

    result = adapter.extract(assets)

    assert result.title == "Titolo Solr Finale"
    assert result.publication_date == "2026-06-03"
    assert result.deadline == "2026-12-15"
    assert "https://www.incentivi.gov.it/files/allegato-a.pdf" in result.attachment_urls
    assert all("/solr/coredrupal/select" not in url for url in result.attachment_urls)
    assert result.raw_fields["source_of_truth"]["title"] == "solr"


def test_incentivi_gov_extract_reads_nested_deadline_and_marks_success(
    tmp_path,
) -> None:
    adapter = IncentiviGovAdapter()
    html_path = tmp_path / "detail.html"
    html_path.write_text(
        "<html><body><h1>Titolo HTML</h1></body></html>", encoding="utf-8"
    )
    json_path = tmp_path / "solr_doc_nested.json"
    json_path.write_text(
        json.dumps(
            {
                "id": "doc-nested",
                "title": "Titolo Solr",
                "data_pubblicazione": {"value": "02/06/2026"},
                "termine_presentazione": {"value": "31/07/2026 ore 12:00"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assets = [
        EvidenceAsset(
            id="asset-html",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.HTML,
            mime_type="text/html",
            original_url="https://www.incentivi.gov.it/it/catalogo/incentivo-test",
            local_path=str(html_path),
            hash=hash_content(html_path.read_bytes()),
            file_size=html_path.stat().st_size,
        ),
        EvidenceAsset(
            id="asset-json",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.JSON,
            mime_type="application/json",
            original_url="https://www.incentivi.gov.it/solr/coredrupal/select",
            local_path=str(json_path),
            hash=hash_content(json_path.read_bytes()),
            file_size=json_path.stat().st_size,
        ),
    ]

    result = adapter.extract(assets)

    assert result.publication_date == "2026-06-02"
    assert result.deadline == "2026-07-31"
    assert result.status == ExtractionStatus.SUCCESS


def test_incentivi_gov_extract_success_without_deadline_if_publication_present(
    tmp_path,
) -> None:
    adapter = IncentiviGovAdapter()
    html_path = tmp_path / "detail.html"
    html_path.write_text(
        "<html><body><h1>Titolo HTML</h1></body></html>", encoding="utf-8"
    )
    json_path = tmp_path / "solr_doc_no_deadline.json"
    json_path.write_text(
        json.dumps(
            {
                "id": "doc-no-deadline",
                "title": "Titolo Solr",
                "data_pubblicazione": "01/06/2026",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assets = [
        EvidenceAsset(
            id="asset-html",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.HTML,
            mime_type="text/html",
            original_url="https://www.incentivi.gov.it/it/catalogo/incentivo-test",
            local_path=str(html_path),
            hash=hash_content(html_path.read_bytes()),
            file_size=html_path.stat().st_size,
        ),
        EvidenceAsset(
            id="asset-json",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.JSON,
            mime_type="application/json",
            original_url="https://www.incentivi.gov.it/solr/coredrupal/select",
            local_path=str(json_path),
            hash=hash_content(json_path.read_bytes()),
            file_size=json_path.stat().st_size,
        ),
    ]

    result = adapter.extract(assets)

    assert result.deadline is None
    assert result.publication_date == "2026-06-01"
    assert result.status == ExtractionStatus.SUCCESS


def test_incentivi_gov_extract_deadline_from_html_fallback_block(
    tmp_path,
) -> None:
    adapter = IncentiviGovAdapter()
    html_path = tmp_path / "detail_with_block.html"
    html_path.write_text(
        """
        <html><body>
            <h1>Titolo incentivo</h1>
            <table>
                <tr><th>Termine di presentazione delle domande</th><td>31.08.2026 ore 12:00</td></tr>
            </table>
        </body></html>
        """,
        encoding="utf-8",
    )
    json_path = tmp_path / "solr_doc_no_deadline.json"
    json_path.write_text(
        json.dumps(
            {
                "id": "doc-no-deadline",
                "title": "Titolo Solr",
                "data_pubblicazione": "01/06/2026",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assets = [
        EvidenceAsset(
            id="asset-html",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.HTML,
            mime_type="text/html",
            original_url="https://www.incentivi.gov.it/it/catalogo/incentivo-test",
            local_path=str(html_path),
            hash=hash_content(html_path.read_bytes()),
            file_size=html_path.stat().st_size,
        ),
        EvidenceAsset(
            id="asset-json",
            source_id="incentivi_gov",
            fetch_record_id="fetch-1",
            asset_type=AssetType.JSON,
            mime_type="application/json",
            original_url="https://www.incentivi.gov.it/solr/coredrupal/select",
            local_path=str(json_path),
            hash=hash_content(json_path.read_bytes()),
            file_size=json_path.stat().st_size,
        ),
    ]

    result = adapter.extract(assets)

    assert result.deadline == "2026-08-31"
    assert result.raw_fields["source_of_truth"]["deadline"] == "html_fallback_block"
