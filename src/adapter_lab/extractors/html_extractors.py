from __future__ import annotations

from bs4 import BeautifulSoup

from adapter_lab.utils.text_cleaning import clean_whitespace
from adapter_lab.utils.urls import normalize_url


class HtmlExtractor:
    """HTML extraction helpers built on BeautifulSoup and lxml."""

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, 'lxml')

    def extract_title(self, html: str) -> str | None:
        """Extract a likely page title from HTML."""

        soup = self._soup(html)
        for selector in ('h1', 'title', 'h2'):
            node = soup.select_one(selector)
            if node:
                text = clean_whitespace(node.get_text(' ', strip=True))
                if text:
                    return text
        return None

    def extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract absolute links from an HTML document."""

        soup = self._soup(html)
        links: list[str] = []
        seen: set[str] = set()
        for anchor in soup.select('a[href]'):
            href = anchor.get('href')
            if not href:
                continue
            normalized = normalize_url(href, base_url)
            if normalized not in seen:
                seen.add(normalized)
                links.append(normalized)
        return links

    def extract_text(self, html: str) -> str:
        """Extract normalized visible text from HTML."""

        soup = self._soup(html)
        return clean_whitespace(soup.get_text(' ', strip=True))

    def extract_meta_description(self, html: str) -> str | None:
        """Extract the meta description content when present."""

        soup = self._soup(html)
        meta = soup.select_one('meta[name="description"]')
        if meta and meta.get('content'):
            return clean_whitespace(meta['content'])
        return None
