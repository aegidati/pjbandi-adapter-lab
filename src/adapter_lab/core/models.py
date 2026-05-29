from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from adapter_lab.core.types import (
    AdapterStatus,
    AssetId,
    AssetType,
    ExtractionStatus,
    HashStr,
    SourceId,
    SourceType,
)


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


class ModelBase(BaseModel):
    """Base model configuration shared by lab entities."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class SourceDefinition(ModelBase):
    """Static definition for a known funding source."""

    id: SourceId
    name: str
    base_url: HttpUrl
    source_type: SourceType
    start_urls: list[str]
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    adapter_status: AdapterStatus = AdapterStatus.DRAFT

    @field_validator('start_urls')
    @classmethod
    def validate_start_urls(cls, value: list[str]) -> list[str]:
        urls = _unique_strings(value)
        if not urls:
            raise ValueError('start_urls must contain at least one URL')
        return urls

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return _unique_strings(value)


class SourceProfile(ModelBase):
    """Observed profile for an analyzed source URL."""

    source_id: SourceId
    analyzed_url: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    inferred_type: SourceType
    title: str | None = None
    description: str | None = None
    detected_links: list[str] = Field(default_factory=list)
    pagination_pattern: str | None = None
    attachment_links: list[str] = Field(default_factory=list)
    candidate_count_estimate: int = 0
    notes: list[str] = Field(default_factory=list)

    @field_validator('detected_links', 'attachment_links', 'notes')
    @classmethod
    def deduplicate_lists(cls, value: list[str]) -> list[str]:
        return _unique_strings(value)

    @field_validator('candidate_count_estimate')
    @classmethod
    def validate_candidate_count(cls, value: int) -> int:
        return max(value, 0)


class RawCandidate(ModelBase):
    """A raw candidate URL discovered from a source."""

    id: str
    source_id: SourceId
    url: str
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('url')
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value:
            raise ValueError('url must not be empty')
        return value


class FetchRecord(ModelBase):
    """Metadata about a fetch operation and its persisted body."""

    id: str
    candidate_id: str
    source_id: SourceId
    original_url: str
    final_url: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status_code: int
    content_type: str | None = None
    headers_summary: dict[str, str] = Field(default_factory=dict)
    body_hash: HashStr
    local_path: str
    asset_ids: list[AssetId] = Field(default_factory=list)

    @field_validator('status_code')
    @classmethod
    def validate_status_code(cls, value: int) -> int:
        if value < 0 or value > 599:
            raise ValueError('status_code must be between 0 and 599')
        return value

    @field_validator('asset_ids')
    @classmethod
    def deduplicate_asset_ids(cls, value: list[AssetId]) -> list[AssetId]:
        return _unique_strings(value)


class EvidenceAsset(ModelBase):
    """A persisted artifact associated with a fetch record."""

    id: AssetId
    source_id: SourceId
    fetch_record_id: str
    asset_type: AssetType
    mime_type: str | None
    original_url: str
    local_path: str
    hash: HashStr
    file_size: int = 0
    extracted_text_path: str | None = None
    parent_asset_id: AssetId | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, value: int) -> int:
        return max(value, 0)


class ExtractionResult(ModelBase):
    """Structured output produced from one candidate's evidence assets."""

    id: str
    source_id: SourceId
    candidate_id: str
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ExtractionStatus
    title: str | None = None
    publication_date: str | None = None
    deadline: str | None = None
    attachment_urls: list[str] = Field(default_factory=list)
    raw_fields: dict[str, Any] = Field(default_factory=dict)
    semantic_fields: dict[str, Any] = Field(default_factory=dict)
    extraction_notes: list[str] = Field(default_factory=list)

    @field_validator('attachment_urls', 'extraction_notes')
    @classmethod
    def deduplicate_output_lists(cls, value: list[str]) -> list[str]:
        return _unique_strings(value)


class ValidationReport(ModelBase):
    """Summary of adapter quality checks for a source."""

    source_id: SourceId
    validated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_candidates: int = 0
    total_fetched: int = 0
    total_extracted: int = 0
    pdf_presence_ratio: float = 0.0
    missing_title_ratio: float = 0.0
    missing_deadline_ratio: float = 0.0
    extraction_completeness_score: float = 0.0
    checks: list[dict[str, Any]] = Field(default_factory=list)
    passed: bool = False
    notes: list[str] = Field(default_factory=list)

    @field_validator(
        'pdf_presence_ratio',
        'missing_title_ratio',
        'missing_deadline_ratio',
        'extraction_completeness_score',
    )
    @classmethod
    def clamp_scores(cls, value: float) -> float:
        return max(0.0, min(1.0, value))
