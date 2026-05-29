from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AdapterRegistry:
    """Runtime registry for mapping source IDs to adapter classes."""

    def __init__(self) -> None:
        self._registry: dict[str, type[Any]] = {}

    def register(self, source_id: str, adapter_class: type[Any]) -> None:
        """Register an adapter class for a source ID."""

        self._registry[source_id] = adapter_class

    def get(self, source_id: str) -> type[Any]:
        """Return the adapter class for a source ID."""

        if source_id not in self._registry:
            raise KeyError(f"No adapter registered for source_id={source_id}")
        return self._registry[source_id]

    def list_all(self) -> dict[str, type[Any]]:
        """Return all registered adapter classes."""

        return dict(self._registry)


REGISTRY = AdapterRegistry()


def register_adapter(source_id: str) -> Callable[[type[Any]], type[Any]]:
    """Decorator that registers an adapter class in the global registry."""

    def decorator(adapter_class: type[Any]) -> type[Any]:
        REGISTRY.register(source_id, adapter_class)
        return adapter_class

    return decorator
