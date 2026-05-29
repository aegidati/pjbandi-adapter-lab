from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules

_LOADED = False


def load_source_adapters() -> None:
    """Import source adapter modules so their registration decorators run."""

    global _LOADED
    if _LOADED:
        return
    for module_info in iter_modules(__path__):
        if module_info.ispkg or module_info.name.startswith("_"):
            continue
        import_module(f"{__name__}.{module_info.name}")
    _LOADED = True
