from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LocalHost = Annotated[str, Field(pattern=r"^(127\.0\.0\.1|localhost)$")]
APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = APP_ROOT / ".local" / "wifi_guard.sqlite3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WIFI_GUARD_",
        extra="ignore",
    )

    app_name: str = "WiFi Guard"
    mode: str = "demo"
    host: LocalHost = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    database_path: Path = DEFAULT_DATABASE_PATH
    history_limit_per_device: int = Field(default=100, ge=1, le=10_000)
    interface_source: str = "demo"
    job_retention_limit: int = Field(default=100, ge=1, le=1_000)
    worker_poll_seconds: float = Field(default=2.0, ge=0.1, le=60)
    worker_lease_seconds: int = Field(default=30, ge=5, le=3600)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value != "demo":
            raise ValueError(
                "WiFi Guard live mode is not supported in Milestone 3; "
                "set WIFI_GUARD_MODE=demo"
            )
        return value

    @field_validator("interface_source")
    @classmethod
    def validate_interface_source(cls, value: str) -> str:
        if value not in {"demo", "local_metadata"}:
            raise ValueError("interface_source must be demo or local_metadata")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_local_origins(cls, origins: list[str]) -> list[str]:
        allowed_prefixes = ("http://127.0.0.1:", "http://localhost:")
        if not origins:
            raise ValueError("at least one local frontend origin is required")
        if any(not origin.startswith(allowed_prefixes) for origin in origins):
            raise ValueError("CORS origins must use localhost or 127.0.0.1")
        return origins
