from __future__ import annotations

from adapter_lab.utils.hashing import hash_content, hash_string, short_id
from adapter_lab.utils.text_cleaning import clean_whitespace
from adapter_lab.utils.urls import is_pdf_url, normalize_url, url_to_filename


def test_hash_content() -> None:
    assert hash_content(b"hello") == hash_content(b"hello")


def test_hash_string() -> None:
    assert hash_string("hello") == hash_content(b"hello")


def test_short_id() -> None:
    assert len(short_id("hello", length=8)) == 8


def test_clean_whitespace() -> None:
    assert clean_whitespace("  hello\n\nworld  ") == "hello world"


def test_normalize_url() -> None:
    assert normalize_url("/bandi/1", "https://example.com/base/") == "https://example.com/bandi/1"


def test_is_pdf_url() -> None:
    assert is_pdf_url("https://example.com/file.pdf") is True
    assert is_pdf_url("https://example.com/file.html") is False


def test_url_to_filename() -> None:
    assert url_to_filename("https://example.com/files/bando.pdf") == "bando.pdf"
