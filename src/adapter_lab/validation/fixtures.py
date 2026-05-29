from __future__ import annotations

from pathlib import Path
from typing import Any

from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage


class FixtureManager:
    """Manage committed or generated fixtures for a source."""

    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)

    def save_fixture(self, source_id: str, name: str, data: Any) -> Path:
        """Save a source fixture as JSON."""

        path = self.storage.path_for_source(source_id, self.settings.fixtures_dir) / f"{name}.json"
        self.storage.save_json(path, data)
        return path

    def load_fixture(self, source_id: str, name: str) -> Any:
        """Load a source fixture from disk."""

        path = self.storage.path_for_source(source_id, self.settings.fixtures_dir) / f"{name}.json"
        return self.storage.load_json(path)

    def list_fixtures(self, source_id: str) -> list[str]:
        """List available fixture names for a source."""

        path = self.storage.path_for_source(source_id, self.settings.fixtures_dir)
        return sorted(item.stem for item in path.glob("*.json"))
