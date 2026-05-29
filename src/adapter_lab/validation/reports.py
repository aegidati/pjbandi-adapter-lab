from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from adapter_lab.core.models import ValidationReport
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage


class ReportWriter:
    """Write validation reports to disk."""

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)

    def write_validation_report(self, report: ValidationReport) -> Path:
        """Write a full validation report as JSON."""

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        path = self.storage.path_for_source(report.source_id, self.settings.reports_dir) / f"validation-{timestamp}.json"
        self.storage.save_json(path, report)
        return path

    def write_summary_report(self, source_id: str, results: list[Any]) -> Path:
        """Write a simple summary report for arbitrary results."""

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        path = self.storage.path_for_source(source_id, self.settings.reports_dir) / f"summary-{timestamp}.json"
        self.storage.save_json(
            path,
            {"source_id": source_id, "results": results, "generated_at": datetime.now(UTC)},
        )
        return path
