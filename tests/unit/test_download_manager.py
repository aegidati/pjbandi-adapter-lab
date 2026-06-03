from __future__ import annotations

from datetime import UTC, datetime

import httpx

from adapter_lab.core.models import FetchRecord
from adapter_lab.fetchers.download_manager import DownloadManager
from adapter_lab.fetchers.http_fetcher import HttpFetcher


def test_download_many_skips_failed_downloads(monkeypatch) -> None:
    manager = DownloadManager()

    def fake_fetch(
        self, url: str, source_id: str = "generic", candidate_id: str | None = None
    ):
        if "missing" in url:
            request = httpx.Request("GET", url)
            response = httpx.Response(status_code=404, request=request)
            raise httpx.HTTPStatusError(
                "Client error '404 Not Found'",
                request=request,
                response=response,
            )

        record = FetchRecord(
            id="ok-record",
            candidate_id="ok-candidate",
            source_id=source_id,
            original_url=url,
            final_url=url,
            fetched_at=datetime.now(UTC),
            status_code=200,
            content_type="application/pdf",
            body_hash="abc123",
            local_path="C:/tmp/file.pdf",
        )
        return record, b"%PDF-1.4"

    monkeypatch.setattr(HttpFetcher, "fetch", fake_fetch)

    assets = manager.download_many(
        [
            "https://example.com/ok.pdf",
            "https://example.com/missing.pdf",
            "https://example.com/ok.pdf",
        ],
        source_id="incentivi_gov",
    )

    assert len(assets) == 1
    assert assets[0].original_url == "https://example.com/ok.pdf"


def test_download_many_fail_fast_raises(monkeypatch) -> None:
    manager = DownloadManager()

    def always_fail(
        self, url: str, source_id: str = "generic", candidate_id: str | None = None
    ):
        request = httpx.Request("GET", url)
        response = httpx.Response(status_code=404, request=request)
        raise httpx.HTTPStatusError(
            "Client error '404 Not Found'",
            request=request,
            response=response,
        )

    monkeypatch.setattr(HttpFetcher, "fetch", always_fail)

    try:
        manager.download_many(
            ["https://example.com/missing.pdf"],
            source_id="incentivi_gov",
            fail_fast=True,
        )
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("Expected HTTPStatusError with fail_fast=True")
