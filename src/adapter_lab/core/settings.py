from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    raw_dir: Path = Field(default=Path("data/raw"), alias="RAW_DIR")
    extracted_dir: Path = Field(
        default=Path("data/extracted"), alias="EXTRACTED_DIR"
    )
    profiles_dir: Path = Field(
        default=Path("data/profiles"), alias="PROFILES_DIR"
    )
    fixtures_dir: Path = Field(
        default=Path("data/fixtures"), alias="FIXTURES_DIR"
    )
    reports_dir: Path = Field(
        default=Path("data/reports"), alias="REPORTS_DIR"
    )

    http_timeout: int = Field(default=30, alias="HTTP_TIMEOUT")
    http_max_retries: int = Field(default=3, alias="HTTP_MAX_RETRIES")
    http_verify_ssl: bool = Field(default=True, alias="HTTP_VERIFY_SSL")
    http_ca_bundle: Path | None = Field(default=None, alias="HTTP_CA_BUNDLE")
    user_agent: str = Field(
        default="AdapterLab/0.1 (+https://github.com/aegidati/pjbandi-adapter-lab)",
        alias="USER_AGENT",
    )

    llm_provider: str | None = Field(default=None, alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def http_verify_value(self) -> bool | str:
        """Return the TLS verification value accepted by httpx."""

        if not self.http_verify_ssl:
            return False
        if self.http_ca_bundle is not None:
            return str(self.http_ca_bundle.expanduser())
        return True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
