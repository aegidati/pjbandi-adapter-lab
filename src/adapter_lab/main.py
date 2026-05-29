from __future__ import annotations

import typer

from adapter_lab.cli.analyze import analyze_cmd
from adapter_lab.cli.discover import discover_cmd
from adapter_lab.cli.extract import extract_cmd
from adapter_lab.cli.fetch import fetch_cmd
from adapter_lab.cli.validate import validate_cmd
from adapter_lab.utils.logging import setup_logging

app = typer.Typer(
    add_completion=False,
    help="Adapter Lab CLI for discovering, prototyping, and validating funding source adapters.",
    no_args_is_help=True,
)


def _load_adapters() -> None:
    import adapter_lab.adapters.sources.incentivi_gov  # noqa: F401
    import adapter_lab.adapters.sources.mimit  # noqa: F401
    import adapter_lab.adapters.sources.veneto_bandi  # noqa: F401


@app.callback()
def main() -> None:
    """Initialize logging and ensure built-in adapters are registered."""
    setup_logging()
    _load_adapters()


app.command("analyze")(analyze_cmd)
app.command("discover")(discover_cmd)
app.command("fetch")(fetch_cmd)
app.command("extract")(extract_cmd)
app.command("validate")(validate_cmd)


if __name__ == "__main__":
    app()
