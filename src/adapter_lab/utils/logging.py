from __future__ import annotations

import logging

from rich.logging import RichHandler

from adapter_lab.core.settings import get_settings


def setup_logging(level: str | None = None) -> None:
    """Configure application logging with Rich output."""

    resolved_level = (level or get_settings().log_level).upper()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(resolved_level)
        return
    logging.basicConfig(
        level=resolved_level,
        format='%(message)s',
        datefmt='[%X]',
        handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""

    return logging.getLogger(name)
