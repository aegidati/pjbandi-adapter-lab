from __future__ import annotations

from adapter_lab.core.models import ExtractionResult, FetchRecord, RawCandidate
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage
from adapter_lab.validation.checks import (
    CheckResult,
    check_candidate_count,
    check_deadline_completeness,
    check_extraction_completeness,
    check_fetch_coverage,
    check_title_completeness,
)
from adapter_lab.validation.fixtures import FixtureManager


class RegressionRunner:
    """Run fixture-backed regression checks for a source."""

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)
        self.fixtures = FixtureManager(self.settings, self.storage)

    def run(self, source_id: str) -> list[CheckResult]:
        """Run all checks for a source using current stored outputs."""

        return self.run_all_checks(source_id)

    def compare_to_fixture(self, current: object, fixture_name: str) -> bool:
        """Compare a current object with a named fixture payload."""

        fixture = self.fixtures.load_fixture("regression", fixture_name)
        if hasattr(current, "model_dump"):
            current = current.model_dump(mode="json")
        return current == fixture

    def run_all_checks(self, source_id: str) -> list[CheckResult]:
        """Load current source artifacts and execute built-in checks."""

        source_raw = self.storage.path_for_source(source_id, self.settings.raw_dir)
        source_extracted = self.storage.path_for_source(source_id, self.settings.extracted_dir)
        candidates_path = source_raw / "candidates.ndjson"
        fetched_path = source_raw / "fetch_records.ndjson"
        extractions_path = source_extracted / "extractions.ndjson"
        candidate_records = self.storage.load_ndjson(candidates_path) if candidates_path.exists() else []
        fetch_records = self.storage.load_ndjson(fetched_path) if fetched_path.exists() else []
        extraction_records = self.storage.load_ndjson(extractions_path) if extractions_path.exists() else []
        candidates = [RawCandidate(**record) for record in candidate_records]
        fetched = [FetchRecord(**record) for record in fetch_records]
        extractions = [ExtractionResult(**record) for record in extraction_records]
        return [
            check_candidate_count(candidates),
            check_fetch_coverage(candidates, fetched),
            check_title_completeness(extractions),
            check_deadline_completeness(extractions),
            check_extraction_completeness(extractions),
        ]
