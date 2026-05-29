from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from adapter_lab.core.pipeline import Pipeline

console = Console()


def extract_cmd(
    source: str = typer.Argument(..., help="Source ID"),
    limit: int | None = typer.Option(None, help="Limit extracted candidates"),
) -> None:
    """Extract structured results for a source."""

    results = Pipeline().run_extract(source, limit)
    table = Table(title=f"Extraction results for {source}")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Title", overflow="fold")
    table.add_column("Deadline")
    for result in results:
        table.add_row(result.id, result.status.value, result.title or "-", result.deadline or "-")
    console.print(table)
    console.print(f"[green]Extraction results:[/green] {len(results)}")
