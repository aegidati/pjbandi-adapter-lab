from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from adapter_lab.core.models import EvidenceAsset, ExtractionResult, FetchRecord, RawCandidate
from adapter_lab.core.types import AssetType, ExtractionStatus


@dataclass(slots=True)
class CheckResult:
    """Outcome of a validation check."""

    name: str
    passed: bool
    score: float
    message: str


@dataclass(slots=True)
class ValidationCheck:
    """Definition for a reusable validation check."""

    name: str
    run: Callable[..., CheckResult]


def check_candidate_count(candidates: list[RawCandidate]) -> CheckResult:
    total = len(candidates)
    return CheckResult(
        name="candidate_count",
        passed=total > 0,
        score=1.0 if total > 0 else 0.0,
        message=f"Discovered {total} candidates.",
    )


def check_fetch_coverage(candidates: list[RawCandidate], fetched: list[FetchRecord]) -> CheckResult:
    total = len(candidates)
    ratio = len(fetched) / total if total else 0.0
    return CheckResult(
        name="fetch_coverage",
        passed=ratio >= 0.8 if total else False,
        score=ratio,
        message=f"Fetched {len(fetched)} of {total} discovered candidates.",
    )


def check_pdf_presence(assets: list[EvidenceAsset]) -> CheckResult:
    total = len(assets)
    ratio = sum(1 for asset in assets if asset.asset_type == AssetType.PDF) / total if total else 0.0
    return CheckResult(
        name="pdf_presence",
        passed=ratio >= 0.2 if total else False,
        score=ratio,
        message=f"PDF assets account for {ratio:.0%} of fetched assets.",
    )


def check_title_completeness(extractions: list[ExtractionResult]) -> CheckResult:
    total = len(extractions)
    ratio = sum(1 for item in extractions if item.title) / total if total else 0.0
    return CheckResult(
        name="title_completeness",
        passed=ratio >= 0.8 if total else False,
        score=ratio,
        message=f"Titles present for {ratio:.0%} of extractions.",
    )


def check_deadline_completeness(extractions: list[ExtractionResult]) -> CheckResult:
    total = len(extractions)
    ratio = sum(1 for item in extractions if item.deadline) / total if total else 0.0
    return CheckResult(
        name="deadline_completeness",
        passed=ratio >= 0.5 if total else False,
        score=ratio,
        message=f"Deadlines present for {ratio:.0%} of extractions.",
    )


def check_extraction_completeness(extractions: list[ExtractionResult]) -> CheckResult:
    total = len(extractions)
    ratio = sum(1 for item in extractions if item.status == ExtractionStatus.SUCCESS) / total if total else 0.0
    return CheckResult(
        name="extraction_completeness",
        passed=ratio >= 0.5 if total else False,
        score=ratio,
        message=f"Fully successful extractions: {ratio:.0%}.",
    )


BUILTIN_CHECKS = [
    ValidationCheck("candidate_count", check_candidate_count),
    ValidationCheck("fetch_coverage", check_fetch_coverage),
    ValidationCheck("pdf_presence", check_pdf_presence),
    ValidationCheck("title_completeness", check_title_completeness),
    ValidationCheck("deadline_completeness", check_deadline_completeness),
    ValidationCheck("extraction_completeness", check_extraction_completeness),
]
