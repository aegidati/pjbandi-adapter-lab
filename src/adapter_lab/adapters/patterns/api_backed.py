from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from adapter_lab.adapters.base import BaseAdapter
from adapter_lab.core.models import EvidenceAsset, ExtractionResult, FetchRecord, RawCandidate
from adapter_lab.utils.hashing import short_id
from adapter_lab.utils.urls import normalize_url


class ApiBackedAdapter(BaseAdapter):
    """Adapter for sources exposing candidate data through JSON APIs."""

    def discover(self) -> list[RawCandidate]:
        endpoint = self.source_def.start_urls[0]
        _, body = self.http_fetcher.fetch(endpoint, source_id=self.source_def.id)
        payload = json.loads(body.decode("utf-8"))
        items = payload if isinstance(payload, list) else payload.get("items", [])
        candidates: list[RawCandidate] = []
        for item in items[:50]:
            url = item.get("url") or item.get("link") or normalize_url(str(item.get("id", "")), str(self.source_def.base_url))
            candidates.append(
                RawCandidate(
                    id=short_id(url),
                    source_id=self.source_def.id,
                    url=url,
                    discovered_at=datetime.now(UTC),
                    title=item.get("title"),
                    metadata={"item": item},
                )
            )
        return candidates

    def fetch(self, candidate: RawCandidate) -> tuple[FetchRecord, list[EvidenceAsset]]:
        record, body = self.http_fetcher.fetch(
            candidate.url,
            source_id=self.source_def.id,
            candidate_id=candidate.id,
        )
        asset = self._asset_from_fetch(record, candidate.url, body)
        record.asset_ids = [asset.id]
        return record, [asset]

    def extract(self, assets: list[EvidenceAsset]) -> ExtractionResult:
        asset = assets[0]
        payload = json.loads(Path(asset.local_path).read_text(encoding="utf-8"))
        text = json.dumps(payload, ensure_ascii=False)
        return self._build_result(
            candidate_id="",
            combined_text=text,
            attachment_urls=[],
            title=payload.get("title") if isinstance(payload, dict) else None,
            raw_fields=payload if isinstance(payload, dict) else {"items": payload},
        )
