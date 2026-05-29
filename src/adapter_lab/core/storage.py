from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from adapter_lab.core.settings import Settings, get_settings


class Storage:
    """Filesystem storage helpers for lab artifacts."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def ensure_dir(self, path: Path) -> Path:
        """Ensure that a directory exists and return it."""

        path.mkdir(parents=True, exist_ok=True)
        return path

    def _to_serializable(self, data: Any) -> Any:
        if hasattr(data, "model_dump"):
            return data.model_dump(mode="json")
        if isinstance(data, Path):
            return str(data)
        if isinstance(data, list):
            return [self._to_serializable(item) for item in data]
        if isinstance(data, dict):
            return {str(key): self._to_serializable(value) for key, value in data.items()}
        return data

    def save_json(self, path: Path, data: Any) -> Path:
        """Save a JSON document to disk."""

        self.ensure_dir(path.parent)
        path.write_text(
            json.dumps(self._to_serializable(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load_json(self, path: Path) -> Any:
        """Load a JSON document from disk."""

        return json.loads(path.read_text(encoding="utf-8"))

    def save_ndjson(self, path: Path, records: Iterable[Any]) -> Path:
        """Save an iterable of records to newline-delimited JSON."""

        self.ensure_dir(path.parent)
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(self._to_serializable(record), ensure_ascii=False) + "\n")
        return path

    def load_ndjson(self, path: Path) -> list[Any]:
        """Load newline-delimited JSON from disk."""

        records: list[Any] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def save_bytes(self, path: Path, data: bytes) -> Path:
        """Save binary content to disk."""

        self.ensure_dir(path.parent)
        path.write_bytes(data)
        return path

    def load_bytes(self, path: Path) -> bytes:
        """Load binary content from disk."""

        return path.read_bytes()

    def path_for_source(self, source_id: str, subdir: str | Path) -> Path:
        """Return a directory path for a source inside a configured subdir."""

        base = Path(subdir)
        return self.ensure_dir(base / source_id)

    def path_for_asset(self, source_id: str, asset_id: str, ext: str) -> Path:
        """Return a stable path for a binary asset under raw storage."""

        extension = ext if ext.startswith(".") else f".{ext}"
        return self.path_for_source(source_id, self.settings.raw_dir) / f"{asset_id}{extension}"
