from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adapter_lab.core.pipeline import Pipeline

console = Console()


def analyze_cmd(url: str = typer.Argument(..., help="Starting URL to analyze")) -> None:
    """Analyze a URL and save the inferred source profile."""

    profile = Pipeline().run_analyze(url)
    table = Table(title="Source Analysis")
    table.add_column("Field")
    table.add_column("Value", overflow="fold")
    table.add_row("Source ID", profile.source_id)
    table.add_row("Analyzed URL", profile.analyzed_url)
    table.add_row("Inferred Type", profile.inferred_type.value)
    table.add_row("Title", profile.title or "-")
    table.add_row("Description", profile.description or "-")
    table.add_row("Candidates", str(profile.candidate_count_estimate))
    table.add_row("Pagination", profile.pagination_pattern or "-")
    console.print(table)
    if profile.detected_links:
        console.print(Panel("\n".join(profile.detected_links[:10]), title="Detected Links"))
