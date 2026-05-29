from __future__ import annotations

import hashlib


def hash_content(content: bytes) -> str:
    """Return the SHA-256 hash of binary content."""

    return hashlib.sha256(content).hexdigest()


def hash_string(s: str) -> str:
    """Return the SHA-256 hash of a string."""

    return hash_content(s.encode('utf-8'))


def short_id(s: str, length: int = 12) -> str:
    """Return a short stable identifier derived from a string."""

    return hash_string(s)[:length]
