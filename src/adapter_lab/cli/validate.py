from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from adapter_lab.core.pipeline import Pipeline

console = Console()


def validate_cmd(source: str = typer.Argument(..., help="Source ID")) -> None:
    """Validate a source adapter and print summary checks."""

    report = Pipeline().run_validate(source)
    table = Table(title=f"Validation report for {source}")
    table.add_column("Check")
    table.add_column("Passed")
    table.add_column("Score")
    table.add_column("Message", overflow="fold")
    for check in report.checks:
        table.add_row(check["name"], "yes" if check["passed"] else "no", f"{check['score']:.2f}", check["message"])
    console.print(table)
    console.print(f"[bold]Passed:[/bold] {report.passed}")
