from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.core.models import EvidenceAsset, ExtractionResult, FetchRecord, RawCandidate, SourceDefinition
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage
from adapter_lab.core.types import AssetType, ExtractionStatus
from adapter_lab.extractors.html_extractors import HtmlExtractor
from adapter_lab.extractors.llm_enrichment import LlmEnricherFactory
from adapter_lab.extractors.pdf_extractors import PdfExtractor
from adapter_lab.extractors.regex_extractors import DeterministicExtractor
from adapter_lab.fetchers.content_detector import ContentDetector
from adapter_lab.fetchers.download_manager import DownloadManager
from adapter_lab.fetchers.http_fetcher import HttpFetcher
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import is_doc_url, is_pdf_url


class BaseAdapter(ABC):
    """Abstract base class for all source adapters."""

    source_def: SourceDefinition

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)
        self.http_fetcher = HttpFetcher(self.settings, self.storage)
        self.download_manager = DownloadManager(self.settings, self.storage)
        self.content_detector = ContentDetector()
        self.html_extractor = HtmlExtractor()
        self.pdf_extractor = PdfExtractor()
        self.regex_extractor = DeterministicExtractor()
        self.enricher = LlmEnricherFactory.create(self.settings.llm_provider)

    @abstractmethod
    def discover(self) -> list[RawCandidate]:
        """Discover candidate records from the source."""

    @abstractmethod
    def fetch(self, candidate: RawCandidate) -> tuple[FetchRecord, list[EvidenceAsset]]:
        """Fetch a candidate and return the fetch record plus associated evidence assets."""

    @abstractmethod
    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        """Extract a structured result from fetched evidence assets."""

    def run_pipeline(self, limit: int | None = None) -> list[ExtractionResult]:
        """Run the default discover, fetch, and extract pipeline."""

        results: list[ExtractionResult] = []
        candidates = self.discover()
        if limit is not None:
            candidates = candidates[:limit]
        for candidate in candidates:
            record, assets = self.fetch(candidate)
            result = self.extract(assets)
            if not result.candidate_id:
                result.candidate_id = record.candidate_id
            results.append(result)
        return results

    def _asset_from_fetch(
        self,
        record: FetchRecord,
        original_url: str,
        body: bytes,
        parent_asset_id: str | None = None,
    ) -> EvidenceAsset:
        asset_type = self.content_detector.detect_type(record.content_type, record.final_url, body)
        return EvidenceAsset(
            id=short_id(f"{record.id}:{original_url}"),
            source_id=self.source_def.id,
            fetch_record_id=record.id,
            asset_type=asset_type,
            mime_type=record.content_type,
            original_url=original_url,
            local_path=record.local_path,
            hash=record.body_hash,
            file_size=len(body),
            parent_asset_id=parent_asset_id,
            fetched_at=record.fetched_at,
        )

    def _download_linked_assets(
        self,
        html: str,
        base_url: str,
        parent_asset_id: str | None = None,
    ) -> list[EvidenceAsset]:
        links = self.html_extractor.extract_links(html, base_url)
        attachments = [link for link in links if is_pdf_url(link) or is_doc_url(link)]
        assets: list[EvidenceAsset] = []
        for asset in self.download_manager.download_many(attachments[:10], self.source_def.id):
            asset.parent_asset_id = parent_asset_id
            assets.append(asset)
        return assets

    def _build_result(
        self,
        candidate_id: str,
        combined_text: str,
        attachment_urls: list[str],
        title: str | None = None,
        status: ExtractionStatus | None = None,
        notes: list[str] | None = None,
        raw_fields: dict[str, object] | None = None,
    ) -> ExtractionResult:
        extraction_status = status or ExtractionStatus.SUCCESS
        extracted_title = title or self.regex_extractor.extract_title(combined_text)
        deadline = self.regex_extractor.extract_deadline(combined_text)
        publication_date = self.regex_extractor.extract_publication_date(combined_text)
        semantic_fields = self.enricher.enrich(combined_text, {"title": extracted_title})
        if not combined_text.strip():
            extraction_status = ExtractionStatus.FAILED
        elif not extracted_title or not deadline:
            extraction_status = ExtractionStatus.PARTIAL
        return ExtractionResult(
            id=short_id(f"{candidate_id}:{datetime.now(UTC).isoformat()}"),
            source_id=self.source_def.id,
            candidate_id=candidate_id,
            extracted_at=datetime.now(UTC),
            status=extraction_status,
            title=extracted_title,
            publication_date=publication_date,
            deadline=deadline,
            attachment_urls=attachment_urls,
            raw_fields=raw_fields or {},
            semantic_fields=semantic_fields,
            extraction_notes=notes or [],
        )

    def _read_asset_text(self, asset: EvidenceAsset) -> str:
        path = Path(asset.local_path)
        if asset.asset_type == AssetType.PDF:
            return self.pdf_extractor.extract_text_from_file(path)
        if asset.asset_type == AssetType.HTML:
            return self.html_extractor.extract_text(path.read_text(encoding="utf-8", errors="ignore"))
        return path.read_text(encoding="utf-8", errors="ignore")
