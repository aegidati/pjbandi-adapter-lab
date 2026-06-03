from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from adapter_lab.core.models import FetchRecord
from adapter_lab.core.settings import Settings, get_settings
from adapter_lab.core.storage import Storage
from adapter_lab.utils.hashing import hash_content, short_id
from adapter_lab.utils.logging import get_logger

LOGGER = get_logger(__name__)


class HttpFetcher:
    """HTTP fetcher with retries and on-disk persistence of fetched bodies."""

    def __init__(
        self,
        settings: Settings | None = None,
        storage: Storage | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or Storage(self.settings)
        if not self.settings.http_verify_ssl:
            LOGGER.warning(
                "HTTP SSL verification is disabled via "
                "HTTP_VERIFY_SSL=false; use only in trusted "
                "environments."
            )

    def get_headers(self) -> dict[str, str]:
        """Return default request headers."""

        return {"User-Agent": self.settings.user_agent}

    def _extension_for(self, url: str, content_type: str | None) -> str:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix
        if suffix:
            return suffix
        lowered = (content_type or "").lower()
        if "html" in lowered:
            return ".html"
        if "pdf" in lowered:
            return ".pdf"
        if "json" in lowered:
            return ".json"
        return ".bin"

    def fetch(
        self,
        url: str,
        source_id: str = "generic",
        candidate_id: str | None = None,
    ) -> tuple[FetchRecord, bytes]:
        """Fetch a URL, persist the response body, and return fetch metadata plus bytes."""

        timeout = httpx.Timeout(self.settings.http_timeout)
        last_error: Exception | None = None
        with httpx.Client(
            follow_redirects=True,
            headers=self.get_headers(),
            timeout=timeout,
            verify=self.settings.http_verify_value(),
        ) as client:
            for attempt in range(1, self.settings.http_max_retries + 1):
                try:
                    response = client.get(url)
                    if response.status_code >= 400:
                        response.raise_for_status()
                    break
                except httpx.HTTPError as exc:
                    last_error = exc
                    LOGGER.warning(
                        "Fetch attempt %s/%s failed for %s: %s",
                        attempt,
                        self.settings.http_max_retries,
                        url,
                        exc,
                    )
                    if attempt == self.settings.http_max_retries:
                        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                            raise RuntimeError(
                                "TLS certificate verification failed while "
                                f"fetching {url}. Set HTTP_CA_BUNDLE to your "
                                "trusted corporate/root CA or, for local "
                                "debugging only, set HTTP_VERIFY_SSL=false."
                            ) from exc
                        raise
            else:
                raise RuntimeError(f"Unable to fetch {url}: {last_error}")

        body = response.content
        body_hash = hash_content(body)
        record_id = short_id(
            f"{url}:{body_hash}:{datetime.now(UTC).isoformat()}"
        )
        local_path = self.storage.path_for_asset(
            source_id,
            record_id,
            self._extension_for(
                str(response.url), response.headers.get("content-type")
            ),
        )
        self.storage.save_bytes(local_path, body)
        headers_summary = {
            key: value
            for key, value in response.headers.items()
            if key.lower()
            in {"content-type", "content-length", "last-modified", "etag"}
        }
        record = FetchRecord(
            id=record_id,
            candidate_id=candidate_id or short_id(url),
            source_id=source_id,
            original_url=url,
            final_url=str(response.url),
            fetched_at=datetime.now(UTC),
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            headers_summary=headers_summary,
            body_hash=body_hash,
            local_path=str(local_path),
        )
        return record, body
