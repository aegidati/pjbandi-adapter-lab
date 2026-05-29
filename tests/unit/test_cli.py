from __future__ import annotations

from typer.testing import CliRunner

from adapter_lab.core.models import RawCandidate
from adapter_lab.main import app

runner = CliRunner()


def test_cli_help_lists_core_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("analyze", "discover", "fetch", "extract", "validate"):
        assert command in result.stdout


def test_cli_discover_uses_registered_sources(monkeypatch) -> None:
    def fake_run_discover(self, source: str) -> list[RawCandidate]:
        assert source == "veneto_bandi"
        return [
            RawCandidate(
                id="cand-1",
                source_id=source,
                url="https://example.com/bandi/1",
                title="Bando Uno",
            )
        ]

    monkeypatch.setattr("adapter_lab.cli.discover.Pipeline.run_discover", fake_run_discover)

    result = runner.invoke(app, ["discover", "veneto_bandi"])

    assert result.exit_code == 0
    assert "Bando Uno" in result.stdout
    assert "Total candidates:" in result.stdout


def test_cli_callback_autoloads_source_adapters(monkeypatch) -> None:
    called = {"value": False}

    monkeypatch.setattr("adapter_lab.cli.discover.Pipeline.run_discover", lambda self, source: [])
    monkeypatch.setattr(
        "adapter_lab.main.load_source_adapters",
        lambda: called.__setitem__("value", True),
    )

    result = runner.invoke(app, ["discover", "veneto_bandi"])

    assert result.exit_code == 0
    assert called["value"] is True
