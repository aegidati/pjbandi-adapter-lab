from __future__ import annotations

from pathlib import Path

from adapter_lab.core.settings import Settings


def test_http_verify_value_defaults_to_true() -> None:
    settings = Settings()
    settings.http_verify_ssl = True

    assert settings.http_verify_value() is True


def test_http_verify_value_uses_ca_bundle_when_provided(
    tmp_path: Path,
) -> None:
    ca_bundle = tmp_path / "corp-ca.pem"
    ca_bundle.write_text("dummy-ca", encoding="utf-8")
    settings = Settings()
    settings.http_verify_ssl = True
    settings.http_ca_bundle = ca_bundle

    assert settings.http_verify_value() == str(ca_bundle)


def test_http_verify_value_can_disable_ssl_verification() -> None:
    settings = Settings()
    settings.http_verify_ssl = False

    assert settings.http_verify_value() is False
