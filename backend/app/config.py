"""Runtime configuration, read from environment variables prefixed with MUJEAZ_."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MUJEAZ_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"

    # Runtime connection: the non-owner application role (subject to Row-Level Security).
    database_url: str = "postgresql+psycopg://mujeaz_app:mujeaz_app@localhost:5432/mujeaz"
    # Owner connection: used only by migrations and the seeder.
    owner_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mujeaz"
    app_db_password: str = "mujeaz_app"  # noqa: S105 — local development default; set in every deployment

    # Authentication (ADR 0003)
    dev_auth: bool = True
    jwt_issuer: str = "mujeaz-dev-idp"
    jwt_audience: str = "mujeaz-api"
    jwt_ttl_minutes: int = 480
    jwt_private_key_pem: str | None = None
    jwks_url: str | None = None

    # AI
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", validation_alias="GEMINI_MODEL")

    # API limits
    max_note_chars: int = 20_000
    rate_limit_per_minute: int = 20
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    @model_validator(mode="after")
    def _no_dev_auth_in_production(self) -> "Settings":
        if self.env == "production" and self.dev_auth:
            raise ValueError("MUJEAZ_DEV_AUTH must be false when MUJEAZ_ENV=production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
