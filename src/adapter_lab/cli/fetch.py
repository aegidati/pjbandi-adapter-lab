from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from adapter_lab.core.pipeline import Pipeline

console = Console()


def fetch_cmd(
    source: str = typer.Argument(..., help="Source ID"),
    limit: int | None = typer.Option(None, help="Limit fetched candidates"),
) -> None:
    """Fetch candidate pages and assets for a source."""

    records = Pipeline().run_fetch(source, limit)
    table = Table(title=f"Fetch results for {source}")
    table.add_column("Record ID")
    table.add_column("Status")
    table.add_column("Content Type")
    table.add_column("Path", overflow="fold")
    for record in records:
        table.add_row(
            record.id, str(record.status_code), record.content_type or "-", record.local_path
        )
    console.print(table)
    console.print(f"[green]Fetched records:[/green] {len(records)}")
