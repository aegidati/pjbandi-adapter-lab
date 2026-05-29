from __future__ import annotations

from datetime import UTC, datetime

from adapter_lab.core.models import (
    EvidenceAsset,
    ExtractionResult,
    FetchRecord,
    RawCandidate,
    SourceDefinition,
    SourceProfile,
    ValidationReport,
)
from adapter_lab.core.types import AdapterStatus, AssetType, ExtractionStatus, SourceType


def test_source_definition_creation() -> None:
    model = SourceDefinition(
        id="veneto_bandi",
        name="Veneto Bandi",
        base_url="https://bandi.regione.veneto.it",
        source_type=SourceType.REGIONAL_HTML_PDF,
        start_urls=["https://bandi.regione.veneto.it/Public/Elenco"],
        tags=["veneto", "bandi", "veneto"],
        adapter_status=AdapterStatus.TESTING,
    )
    assert model.id == "veneto_bandi"
    assert model.tags == ["veneto", "bandi"]


def test_source_profile_creation() -> None:
    profile = SourceProfile(
        source_id="veneto_bandi",
        analyzed_url="https://bandi.regione.veneto.it/Public/Elenco",
        analyzed_at=datetime.now(UTC),
        inferred_type=SourceType.REGIONAL_HTML_PDF,
        detected_links=["https://example.com/a", "https://example.com/a"],
        attachment_links=["a.pdf"],
        notes=["first", "first"],
    )
    assert profile.candidate_count_estimate == 0
    assert profile.detected_links == ["https://example.com/a"]
    assert profile.notes == ["first"]


def test_raw_candidate_creation() -> None:
    candidate = RawCandidate(id="abc123", source_id="src", url="https://example.com/grant")
    assert candidate.id == "abc123"
    assert candidate.metadata == {}


def test_fetch_record_creation() -> None:
    record = FetchRecord(
        id="fetch1",
        candidate_id="cand1",
        source_id="src",
        original_url="https://example.com/original",
        final_url="https://example.com/final",
        fetched_at=datetime.now(UTC),
        status_code=200,
        content_type="text/html",
        body_hash="hash",
        local_path="data/raw/src/fetch1.html",
        asset_ids=["a1", "a1"],
    )
    assert record.status_code == 200
    assert record.asset_ids == ["a1"]


def test_evidence_asset_creation() -> None:
    asset = EvidenceAsset(
        id="asset1",
        source_id="src",
        fetch_record_id="fetch1",
        asset_type=AssetType.PDF,
        mime_type="application/pdf",
        original_url="https://example.com/file.pdf",
        local_path="data/raw/src/file.pdf",
        hash="hash",
        file_size=123,
        fetched_at=datetime.now(UTC),
    )
    assert asset.asset_type == AssetType.PDF
    assert asset.file_size == 123


def test_extraction_result_creation() -> None:
    result = ExtractionResult(
        id="ext1",
        source_id="src",
        candidate_id="cand1",
        extracted_at=datetime.now(UTC),
        status=ExtractionStatus.SUCCESS,
        title="Bando Energia",
        attachment_urls=["https://example.com/a.pdf"],
        raw_fields={"budget": "€ 100.000"},
    )
    assert result.status == ExtractionStatus.SUCCESS
    assert result.title == "Bando Energia"


def test_validation_report_creation() -> None:
    report = ValidationReport(
        source_id="src",
        validated_at=datetime.now(UTC),
        total_candidates=10,
        total_fetched=9,
        total_extracted=8,
        pdf_presence_ratio=1.5,
        missing_title_ratio=-1,
        extraction_completeness_score=0.75,
    )
    assert report.pdf_presence_ratio == 1.0
    assert report.missing_title_ratio == 0.0
    assert report.extraction_completeness_score == 0.75
