from __future__ import annotations

from adapter_lab.extractors.html_extractors import HtmlExtractor
from adapter_lab.extractors.regex_extractors import DeterministicExtractor
from adapter_lab.fetchers.content_detector import ContentDetector
from adapter_lab.core.types import AssetType


def test_html_extract_title() -> None:
    html = "<html><head><title>Bando Energia</title></head><body></body></html>"
    assert HtmlExtractor().extract_title(html) == "Bando Energia"


def test_html_extract_links() -> None:
    html = '<a href="/bandi/1">Uno</a><a href="https://example.com/doc.pdf">PDF</a>'
    links = HtmlExtractor().extract_links(html, "https://example.com/catalogo")
    assert "https://example.com/bandi/1" in links
    assert "https://example.com/doc.pdf" in links


def test_regex_extract_deadline() -> None:
    text = "La scadenza è fissata al 15 gennaio 2025 per la presentazione delle domande."
    assert DeterministicExtractor().extract_deadline(text) == "2025-01-15"


def test_regex_extract_euro_amounts() -> None:
    text = "Dotazione finanziaria pari a € 1.200.000 e contributo massimo 50.000 euro."
    amounts = DeterministicExtractor().extract_euro_amounts(text)
    assert "€ 1.200.000" in amounts
    assert "50.000 euro" in amounts


def test_content_detector_pdf() -> None:
    detector = ContentDetector()
    assert (
        detector.detect_type("application/pdf", "https://example.com/file.pdf", b"%PDF-1.7")
        == AssetType.PDF
    )


def test_content_detector_html() -> None:
    detector = ContentDetector()
    assert (
        detector.detect_type("text/html", "https://example.com", b"<html></html>") == AssetType.HTML
    )
