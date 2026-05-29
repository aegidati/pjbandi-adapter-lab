from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from adapter_lab.utils.logging import get_logger

LOGGER = get_logger(__name__)


class LlmEnricher(ABC):
    """Abstract interface for optional LLM-based enrichment."""

    @abstractmethod
    def enrich(self, text: str, fields_hint: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return enriched semantic fields for extracted text."""


class PlaceholderEnricher(LlmEnricher):
    """Fallback enricher used when no provider is configured."""

    def enrich(self, text: str, fields_hint: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return an empty enrichment payload and log a warning."""

        LOGGER.warning("No LLM is configured; returning empty semantic enrichment payload.")
        return {}


class LlmEnricherFactory:
    """Factory for constructing LLM enrichers."""

    @staticmethod
    def create(provider: str | None) -> LlmEnricher:
        """Return an enricher implementation for the configured provider."""

        return PlaceholderEnricher()
