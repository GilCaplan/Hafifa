from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    host: str
    port: int
    reload: bool
    log_file: Path
    log_level: str
    database_url: str
    aqi_alert_threshold: float = 300
    aqi_average_decimals: int = 2
    best_cities_count: int = 3

    @field_validator("log_file")
    @classmethod
    def resolve_from_project_root(cls, path: Path) -> Path:
        return PROJECT_ROOT / path


settings = Settings()
