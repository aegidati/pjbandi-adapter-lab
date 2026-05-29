from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from adapter_lab.core.pipeline import Pipeline

console = Console()


def discover_cmd(
    source: str = typer.Argument(..., help="Source ID"),
    limit: int | None = typer.Option(None, help="Limit discovered candidates"),
) -> None:
    """Discover candidates for a registered source."""

    candidates = Pipeline().run_discover(source, limit)
    table = Table(title=f"Discovered candidates for {source}")
    table.add_column("ID")
    table.add_column("URL", overflow="fold")
    table.add_column("Title", overflow="fold")
    for candidate in candidates:
        table.add_row(candidate.id, candidate.url, candidate.title or "-")
    console.print(table)
    console.print(f"[green]Total candidates:[/green] {len(candidates)}")
