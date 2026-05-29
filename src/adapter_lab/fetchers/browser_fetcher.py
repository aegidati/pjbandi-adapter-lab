from __future__ import annotations


class BrowserFetcher:
    """Placeholder for future browser-driven fetching of dynamic sources."""

    def fetch(self, url: str) -> bytes:
        """Raise a clear error until browser-based fetching is implemented."""

        raise NotImplementedError(
            'BrowserFetcher is not implemented yet. Use HttpFetcher for static sources '
            'or extend this class for JavaScript-rendered portals.'
        )
