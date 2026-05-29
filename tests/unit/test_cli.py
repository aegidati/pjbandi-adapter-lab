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
    def fake_run_discover(self, source: str, limit: int | None = None) -> list[RawCandidate]:
        assert source == "veneto_bandi"
        assert limit is None
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

    monkeypatch.setattr(
        "adapter_lab.cli.discover.Pipeline.run_discover",
        lambda self, source, limit=None: [],
    )
    monkeypatch.setattr(
        "adapter_lab.main.load_source_adapters",
        lambda: called.__setitem__("value", True),
    )

    result = runner.invoke(app, ["discover", "veneto_bandi"])

    assert result.exit_code == 0
    assert called["value"] is True


def test_cli_discover_forwards_limit_to_pipeline(monkeypatch) -> None:
    captured_limit: int | None = None

    def fake_run_discover(self, source: str, limit: int | None = None) -> list[RawCandidate]:
        nonlocal captured_limit
        assert source == "veneto_bandi"
        captured_limit = limit
        return []

    monkeypatch.setattr("adapter_lab.cli.discover.Pipeline.run_discover", fake_run_discover)

    result = runner.invoke(app, ["discover", "veneto_bandi", "--limit", "3"])

    assert result.exit_code == 0
    assert captured_limit == 3


def test_run_discover_seeds_profile_when_missing(tmp_path, monkeypatch) -> None:
    """run_discover must create a profile JSON from the SourceDefinition when none exists."""
    from adapter_lab.adapters.sources.veneto_bandi import VenetoBandiAdapter
    from adapter_lab.core.pipeline import Pipeline
    from adapter_lab.core.settings import Settings
    from adapter_lab.fetchers.http_fetcher import HttpFetcher

    settings = Settings(
        DATA_DIR=tmp_path / "data",
        RAW_DIR=tmp_path / "data/raw",
        EXTRACTED_DIR=tmp_path / "data/extracted",
        PROFILES_DIR=tmp_path / "data/profiles",
        FIXTURES_DIR=tmp_path / "data/fixtures",
        REPORTS_DIR=tmp_path / "data/reports",
    )
    profiles_dir = settings.profiles_dir
    profiles_dir.mkdir(parents=True, exist_ok=True)

    # Return an empty listing page so discover() returns no candidates.
    def fake_fetch(self, url, source_id="veneto_bandi", candidate_id=None):
        from datetime import UTC, datetime
        from adapter_lab.core.models import FetchRecord
        from adapter_lab.utils.hashing import hash_content

        body = b"<html><body></body></html>"
        out_path = tmp_path / "listing.html"
        out_path.write_bytes(body)
        return (
            FetchRecord(
                id="listing",
                candidate_id="listing",
                source_id=source_id,
                original_url=url,
                final_url=url,
                fetched_at=datetime.now(UTC),
                status_code=200,
                content_type="text/html",
                body_hash=hash_content(body),
                local_path=str(out_path),
            ),
            body,
        )

    monkeypatch.setattr(HttpFetcher, "fetch", fake_fetch)

    pipeline = Pipeline(settings=settings)
    pipeline.run_discover("veneto_bandi")

    profile_file = profiles_dir / "veneto_bandi.json"
    assert profile_file.exists(), "Profile JSON must be created by run_discover"

    import json
    profile_data = json.loads(profile_file.read_text())
    assert profile_data["source_id"] == "veneto_bandi"
    assert profile_data["inferred_type"] == "regional_html_pdf"
    assert profile_data["title"] == VenetoBandiAdapter.source_def.name


def test_run_discover_does_not_overwrite_existing_profile(tmp_path, monkeypatch) -> None:
    """run_discover must not overwrite an existing profile JSON."""
    import json
    from adapter_lab.core.pipeline import Pipeline
    from adapter_lab.core.settings import Settings
    from adapter_lab.fetchers.http_fetcher import HttpFetcher

    settings = Settings(
        DATA_DIR=tmp_path / "data",
        RAW_DIR=tmp_path / "data/raw",
        EXTRACTED_DIR=tmp_path / "data/extracted",
        PROFILES_DIR=tmp_path / "data/profiles",
        FIXTURES_DIR=tmp_path / "data/fixtures",
        REPORTS_DIR=tmp_path / "data/reports",
    )
    profiles_dir = settings.profiles_dir
    profiles_dir.mkdir(parents=True, exist_ok=True)

    existing_profile = profiles_dir / "veneto_bandi.json"
    existing_content = {"source_id": "veneto_bandi", "custom": "do-not-overwrite"}
    existing_profile.write_text(json.dumps(existing_content))

    def fake_fetch(self, url, source_id="veneto_bandi", candidate_id=None):
        from datetime import UTC, datetime
        from adapter_lab.core.models import FetchRecord
        from adapter_lab.utils.hashing import hash_content

        body = b"<html><body></body></html>"
        out_path = tmp_path / "listing.html"
        out_path.write_bytes(body)
        return (
            FetchRecord(
                id="listing",
                candidate_id="listing",
                source_id=source_id,
                original_url=url,
                final_url=url,
                fetched_at=datetime.now(UTC),
                status_code=200,
                content_type="text/html",
                body_hash=hash_content(body),
                local_path=str(out_path),
            ),
            body,
        )

    monkeypatch.setattr(HttpFetcher, "fetch", fake_fetch)

    pipeline = Pipeline(settings=settings)
    pipeline.run_discover("veneto_bandi")

    saved = json.loads(existing_profile.read_text())
    assert saved.get("custom") == "do-not-overwrite", "Existing profile must not be overwritten"
