from __future__ import annotations

from enum import StrEnum

SourceId = str
CandidateUrl = str
CandidateId = str
FetchRecordId = str
AssetId = str
HashStr = str
FilePathStr = str
ProfileId = str
ReportId = str


class SourceType(StrEnum):
    """Supported source shapes used to choose an adapter strategy."""

    CATALOG_HTML = "catalog_html"
    REGIONAL_HTML_PDF = "regional_html_pdf"
    PDF_FIRST = "pdf_first"
    API_BACKED = "api_backed"
    LEGAL_BULLETIN = "legal_bulletin"
    UNKNOWN = "unknown"


class AssetType(StrEnum):
    """Known fetched artifact types."""

    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    DOCX = "docx"
    ZIP = "zip"
    OTHER = "other"


class AdapterStatus(StrEnum):
    """Lifecycle status for an adapter in the lab."""

    DRAFT = "draft"
    TESTING = "testing"
    STABLE = "stable"
    PROMOTED = "promoted"


class ExtractionStatus(StrEnum):
    """Status for an extraction attempt."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
