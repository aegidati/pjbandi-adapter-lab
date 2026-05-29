from __future__ import annotations

from pathlib import Path

from adapter_lab.core.models import SourceDefinition, SourceProfile
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage
from adapter_lab.core.types import SourceType
from adapter_lab.extractors.html_extractors import HtmlExtractor
from adapter_lab.utils.urls import extract_domain


class ProfileBuilder:
    """Create and persist source profiles from analyzed evidence."""

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)
        self.html_extractor = HtmlExtractor()

    def seed_from_definition(self, source_def: SourceDefinition) -> SourceProfile:
        """Create a baseline source profile directly from a SourceDefinition.

        The resulting profile captures the statically known metadata from the
        adapter without performing any live HTTP requests.  It is intended as a
        lightweight placeholder that can later be enriched by running
        ``adapter-lab analyze <url>``.
        """
        notes = [
            "Profile seeded from SourceDefinition; "
            "run `adapter-lab analyze` to populate live evidence."
        ]
        return SourceProfile(
            source_id=source_def.id,
            analyzed_url=source_def.start_urls[0],
            inferred_type=source_def.source_type,
            title=source_def.name,
            description=source_def.notes or None,
            notes=notes,
        )

    def build(
        self,
        url: str,
        html: str,
        analyzed_links: list[str],
        pagination: str | None,
        attachments: list[str],
    ) -> SourceProfile:
        """Build a source profile from analyzed HTML evidence."""

        source_id = extract_domain(url).replace(".", "_").replace("-", "_") or "unknown_source"
        return SourceProfile(
            source_id=source_id,
            analyzed_url=url,
            inferred_type=SourceType.UNKNOWN,
            title=self.html_extractor.extract_title(html),
            description=self.html_extractor.extract_meta_description(html),
            detected_links=analyzed_links,
            pagination_pattern=pagination,
            attachment_links=attachments,
            candidate_count_estimate=len(analyzed_links),
            notes=["Profile created from saved analysis inputs."],
        )

    def save(self, profile: SourceProfile) -> Path:
        """Persist a source profile to the profiles directory."""

        path = self.settings.profiles_dir / f"{profile.source_id}.json"
        self.storage.save_json(path, profile)
        return path
