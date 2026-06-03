from __future__ import annotations

from datetime import UTC, datetime

from adapter_lab.core.models import (
    EvidenceAsset,
    ExtractionResult,
    FetchRecord,
    RawCandidate,
)
from adapter_lab.core.pipeline import Pipeline, SourceRunData
from adapter_lab.core.types import AssetType, ExtractionStatus


def test_run_validate_applies_incentivi_threshold_overrides(
    monkeypatch, tmp_path
) -> None:
    pipeline = Pipeline()

    candidates = [
        RawCandidate(
            id=f"cand-{i}", source_id="incentivi_gov", url=f"https://example.com/{i}"
        )
        for i in range(3)
    ]
    fetch_records = [
        FetchRecord(
            id=f"fetch-{i}",
            candidate_id=f"cand-{i}",
            source_id="incentivi_gov",
            original_url=f"https://example.com/{i}",
            final_url=f"https://example.com/{i}",
            fetched_at=datetime.now(UTC),
            status_code=200,
            content_type="text/html",
            body_hash=f"h{i}",
            local_path=str(tmp_path / f"f{i}.html"),
        )
        for i in range(3)
    ]

    # 1 PDF over 25 assets => 0.04 (below default 0.20, above incentivi override 0.03)
    assets = [
        EvidenceAsset(
            id="asset-pdf",
            source_id="incentivi_gov",
            fetch_record_id="fetch-0",
            asset_type=AssetType.PDF,
            mime_type="application/pdf",
            original_url="https://example.com/a.pdf",
            local_path=str(tmp_path / "a.pdf"),
            hash="hp",
            file_size=100,
        )
    ]
    assets.extend(
        EvidenceAsset(
            id=f"asset-html-{i}",
            source_id="incentivi_gov",
            fetch_record_id="fetch-0",
            asset_type=AssetType.HTML,
            mime_type="text/html",
            original_url=f"https://example.com/{i}.html",
            local_path=str(tmp_path / f"{i}.html"),
            hash=f"hh{i}",
            file_size=10,
        )
        for i in range(24)
    )

    # 1 deadline over 3 extractions => 0.33 (below default 0.50, above incentivi override 0.30)
    extractions = [
        ExtractionResult(
            id="ex-1",
            source_id="incentivi_gov",
            candidate_id="cand-1",
            extracted_at=datetime.now(UTC),
            status=ExtractionStatus.SUCCESS,
            title="Titolo 1",
            publication_date="2026-06-01",
            deadline="2026-06-30",
        ),
        ExtractionResult(
            id="ex-2",
            source_id="incentivi_gov",
            candidate_id="cand-2",
            extracted_at=datetime.now(UTC),
            status=ExtractionStatus.SUCCESS,
            title="Titolo 2",
            publication_date="2026-06-01",
        ),
        ExtractionResult(
            id="ex-3",
            source_id="incentivi_gov",
            candidate_id="cand-3",
            extracted_at=datetime.now(UTC),
            status=ExtractionStatus.SUCCESS,
            title="Titolo 3",
            publication_date="2026-06-01",
        ),
    ]

    monkeypatch.setattr(
        Pipeline,
        "_run_source",
        lambda self, source_id, limit=None, fetch=False, extract=False: SourceRunData(
            candidates=candidates,
            fetch_records=fetch_records,
            assets=assets,
            extractions=extractions,
        ),
    )
    monkeypatch.setattr(
        pipeline.report_writer, "write_validation_report", lambda report: None
    )

    report = pipeline.run_validate("incentivi_gov")

    assert report.passed is True
    checks = {item["name"]: item for item in report.checks}
    assert checks["pdf_presence"]["passed"] is True
    assert checks["deadline_completeness"]["passed"] is True


def test_run_validate_applies_mimit_threshold_overrides(monkeypatch, tmp_path) -> None:
    pipeline = Pipeline()

    candidates = [
        RawCandidate(id=f"cand-{i}", source_id="mimit", url=f"https://example.com/{i}")
        for i in range(3)
    ]
    fetch_records = [
        FetchRecord(
            id=f"fetch-{i}",
            candidate_id=f"cand-{i}",
            source_id="mimit",
            original_url=f"https://example.com/{i}",
            final_url=f"https://example.com/{i}",
            fetched_at=datetime.now(UTC),
            status_code=200,
            content_type="text/html",
            body_hash=f"h{i}",
            local_path=str(tmp_path / f"f{i}.html"),
        )
        for i in range(3)
    ]

    # Keep pdf_presence above default threshold and focus assertions on deadline/extraction.
    assets = [
        EvidenceAsset(
            id="asset-pdf",
            source_id="mimit",
            fetch_record_id="fetch-0",
            asset_type=AssetType.PDF,
            mime_type="application/pdf",
            original_url="https://example.com/a.pdf",
            local_path=str(tmp_path / "a.pdf"),
            hash="hp",
            file_size=100,
        ),
        EvidenceAsset(
            id="asset-html",
            source_id="mimit",
            fetch_record_id="fetch-0",
            asset_type=AssetType.HTML,
            mime_type="text/html",
            original_url="https://example.com/a.html",
            local_path=str(tmp_path / "a.html"),
            hash="hh",
            file_size=10,
        ),
    ]

    # deadline completeness and extraction completeness at 0.33.
    extractions = [
        ExtractionResult(
            id="ex-1",
            source_id="mimit",
            candidate_id="cand-1",
            extracted_at=datetime.now(UTC),
            status=ExtractionStatus.SUCCESS,
            title="Titolo 1",
            publication_date="2026-06-01",
            deadline="2026-06-30",
        ),
        ExtractionResult(
            id="ex-2",
            source_id="mimit",
            candidate_id="cand-2",
            extracted_at=datetime.now(UTC),
            status=ExtractionStatus.PARTIAL,
            title="Titolo 2",
            publication_date="2026-06-01",
        ),
        ExtractionResult(
            id="ex-3",
            source_id="mimit",
            candidate_id="cand-3",
            extracted_at=datetime.now(UTC),
            status=ExtractionStatus.PARTIAL,
            title="Titolo 3",
            publication_date="2026-06-01",
        ),
    ]

    monkeypatch.setattr(
        Pipeline,
        "_run_source",
        lambda self, source_id, limit=None, fetch=False, extract=False: SourceRunData(
            candidates=candidates,
            fetch_records=fetch_records,
            assets=assets,
            extractions=extractions,
        ),
    )
    monkeypatch.setattr(
        pipeline.report_writer, "write_validation_report", lambda report: None
    )

    report = pipeline.run_validate("mimit")

    assert report.passed is True
    checks = {item["name"]: item for item in report.checks}
    assert checks["deadline_completeness"]["passed"] is True
    assert checks["extraction_completeness"]["passed"] is True
