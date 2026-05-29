from __future__ import annotations

from adapter_lab.core.models import EvidenceAsset
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage
from adapter_lab.fetchers.content_detector import ContentDetector
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import short_id


class DownloadManager:
    """Download helper that converts URLs into evidence assets."""

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)
        self.fetcher = HttpFetcher(self.settings, self.storage)
        self.detector = ContentDetector()

    def download_asset(self, url: str, source_id: str) -> EvidenceAsset:
        """Download a single asset and return its metadata."""

        record, body = self.fetcher.fetch(url, source_id=source_id)
        asset_type = self.detector.detect_type(record.content_type, record.final_url, body)
        return EvidenceAsset(
            id=short_id(f"{record.id}:{url}"),
            source_id=source_id,
            fetch_record_id=record.id,
            asset_type=asset_type,
            mime_type=record.content_type,
            original_url=url,
            local_path=record.local_path,
            hash=record.body_hash,
            file_size=len(body),
            fetched_at=record.fetched_at,
        )

    def download_many(self, urls: list[str], source_id: str) -> list[EvidenceAsset]:
        """Download multiple assets for a source."""

        assets: list[EvidenceAsset] = []
        seen: set[str] = set()
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            assets.append(self.download_asset(url, source_id))
        return assets
