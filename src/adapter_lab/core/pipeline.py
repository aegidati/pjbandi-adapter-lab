from __future__ import annotations

from dataclasses import dataclass

from adapter_lab.core.models import (
    EvidenceAsset,
    ExtractionResult,
    FetchRecord,
    RawCandidate,
    SourceProfile,
    ValidationReport,
)
from adapter_lab.core.registry import REGISTRY
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage
from adapter_lab.source_analysis.analyzer import SourceAnalyzer
from adapter_lab.source_analysis.profile_builder import ProfileBuilder
from adapter_lab.validation.checks import (
    CheckResult,
    check_candidate_count,
    check_deadline_completeness,
    check_extraction_completeness,
    check_fetch_coverage,
    check_pdf_presence,
    check_title_completeness,
)
from adapter_lab.validation.reports import ReportWriter


@dataclass
class SourceRunData:
    candidates: list[RawCandidate]
    fetch_records: list[FetchRecord]
    assets: list[EvidenceAsset]
    extractions: list[ExtractionResult]


class Pipeline:
    """High-level orchestration for adapter lab workflows."""

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)
        self.report_writer = ReportWriter(self.settings, self.storage)

    def _get_adapter(self, source_id: str):
        adapter_class = REGISTRY.get(source_id)
        return adapter_class(settings=self.settings, storage=self.storage)

    def _run_source(
        self,
        source_id: str,
        limit: int | None = None,
        *,
        fetch: bool = False,
        extract: bool = False,
    ) -> SourceRunData:
        adapter = self._get_adapter(source_id)
        candidates = adapter.discover()
        if limit is not None:
            candidates = candidates[:limit]

        fetch_records: list[FetchRecord] = []
        assets: list[EvidenceAsset] = []
        extractions: list[ExtractionResult] = []
        if not fetch and not extract:
            return SourceRunData(candidates, fetch_records, assets, extractions)

        for candidate in candidates:
            record, candidate_assets = adapter.fetch(candidate)
            fetch_records.append(record)
            assets.extend(candidate_assets)
            if extract:
                result = adapter.extract(candidate_assets)
                result.candidate_id = candidate.id
                extractions.append(result)

        return SourceRunData(candidates, fetch_records, assets, extractions)

    def run_analyze(self, url: str) -> SourceProfile:
        """Analyze a URL and persist its source profile."""

        analyzer = SourceAnalyzer(self.settings)
        html = analyzer._fetch_page(url)
        links = analyzer._extract_candidate_links(html, url)
        pagination = analyzer._detect_pagination(html, url)
        attachments = analyzer._detect_attachments(html)
        builder = ProfileBuilder(self.settings, self.storage)
        profile = builder.build(url, html, links, pagination, attachments)
        profile.inferred_type = analyzer._detect_source_type(html, url)
        builder.save(profile)
        return profile

    def run_discover(self, source_id: str) -> list[RawCandidate]:
        """Run discovery for a registered source adapter."""

        run = self._run_source(source_id)
        candidates = run.candidates
        path = self.storage.path_for_source(source_id, self.settings.raw_dir) / "candidates.ndjson"
        self.storage.save_ndjson(path, candidates)
        return candidates

    def run_fetch(self, source_id: str, limit: int | None = None) -> list[FetchRecord]:
        """Run fetch for discovered candidates and persist fetch metadata."""

        run = self._run_source(source_id, limit, fetch=True)
        candidates = run.candidates
        fetch_records = run.fetch_records
        assets = run.assets
        raw_dir = self.storage.path_for_source(source_id, self.settings.raw_dir)
        self.storage.save_ndjson(raw_dir / "candidates.ndjson", candidates)
        self.storage.save_ndjson(raw_dir / "fetch_records.ndjson", fetch_records)
        self.storage.save_ndjson(raw_dir / "assets.ndjson", assets)
        return fetch_records

    def run_extract(self, source_id: str, limit: int | None = None) -> list[ExtractionResult]:
        """Run extraction for discovered candidates and persist results."""

        run = self._run_source(source_id, limit, fetch=True, extract=True)
        candidates = run.candidates
        fetch_records = run.fetch_records
        assets = run.assets
        results = run.extractions
        raw_dir = self.storage.path_for_source(source_id, self.settings.raw_dir)
        extracted_dir = self.storage.path_for_source(source_id, self.settings.extracted_dir)
        self.storage.save_ndjson(raw_dir / "candidates.ndjson", candidates)
        self.storage.save_ndjson(raw_dir / "fetch_records.ndjson", fetch_records)
        self.storage.save_ndjson(raw_dir / "assets.ndjson", assets)
        self.storage.save_ndjson(extracted_dir / "extractions.ndjson", results)
        return results

    def run_validate(self, source_id: str) -> ValidationReport:
        """Run end-to-end validation for a source adapter and persist the report."""

        run = self._run_source(source_id, fetch=True, extract=True)
        candidates = run.candidates
        fetch_records = run.fetch_records
        assets = run.assets
        extractions = run.extractions
        checks: list[CheckResult] = [
            check_candidate_count(candidates),
            check_fetch_coverage(candidates, fetch_records),
            check_pdf_presence(assets),
            check_title_completeness(extractions),
            check_deadline_completeness(extractions),
            check_extraction_completeness(extractions),
        ]
        title_check = next(check for check in checks if check.name == "title_completeness")
        deadline_check = next(check for check in checks if check.name == "deadline_completeness")
        extraction_check = next(
            check for check in checks if check.name == "extraction_completeness"
        )
        pdf_check = next(check for check in checks if check.name == "pdf_presence")
        report = ValidationReport(
            source_id=source_id,
            total_candidates=len(candidates),
            total_fetched=len(fetch_records),
            total_extracted=len(extractions),
            pdf_presence_ratio=pdf_check.score,
            missing_title_ratio=1.0 - title_check.score if extractions else 1.0,
            missing_deadline_ratio=1.0 - deadline_check.score if extractions else 1.0,
            extraction_completeness_score=extraction_check.score,
            checks=[check.__dict__ for check in checks],
            passed=all(check.passed for check in checks),
            notes=[check.message for check in checks if not check.passed],
        )
        raw_dir = self.storage.path_for_source(source_id, self.settings.raw_dir)
        extracted_dir = self.storage.path_for_source(source_id, self.settings.extracted_dir)
        self.storage.save_ndjson(raw_dir / "candidates.ndjson", candidates)
        self.storage.save_ndjson(raw_dir / "fetch_records.ndjson", fetch_records)
        self.storage.save_ndjson(raw_dir / "assets.ndjson", assets)
        self.storage.save_ndjson(extracted_dir / "extractions.ndjson", extractions)
        self.report_writer.write_validation_report(report)
        return report
