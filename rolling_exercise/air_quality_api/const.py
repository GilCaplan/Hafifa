import re
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from air_quality_db.models import Alert, Reading

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETUP_DIR = PROJECT_ROOT / "setup"


class Settings(BaseSettings):
    """Settings from environment variables or setup/.env"""

    model_config = SettingsConfigDict(env_file=SETUP_DIR / ".env", extra="ignore")

    # values are in setup/.env
    host: str
    port: int
    reload: bool
    log_file: Path
    log_level: str
    database_url: str

    @field_validator("log_file")
    @classmethod
    def resolve_from_project_root(cls, path: Path) -> Path:
        """Keep the logs in the same folder"""
        return PROJECT_ROOT / path


settings = Settings()


class ColumnSets:
    """
    Groups of the models' column names, for the uploaded CSV in pandas (its columns, after clean_columns, are named
    like the database's). A single column's name comes from its model, e.g. Reading.date.key.
    """

    POLLUTANTS = [Reading.pm25.key, Reading.no2.key, Reading.co2.key]  # noqa: RUF012
    REQUIRED = [Reading.date.key, Reading.city.key, *POLLUTANTS]  # noqa: RUF012
    ALERT = [Alert.date.key, Alert.city.key, Alert.aqi.key]  # noqa: RUF012


class Consts:
    "constants"

    app_path: str = "air_quality_api.api:app"  # what uvicorn loads
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    insert_chunk_size: int = 1000  # rows per INSERT: Postgres allows at most 65,535 values in one statement


class Validation:
    """Input validation for csv and city strings"""

    CSV_EXTENSION = ".csv"
    DATE_FORMAT = "%Y-%m-%d"
    CSV_HEADER_LINES = 1
    MIN_POLLUTANT_VALUE = 0
    # Words of letters (any language) joined by single spaces,
    # hyphens or apostrophes, e.g. "Be'er Sheva"
    CITY_NAME_REGEX = re.compile(r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$")
    MAX_CITY_NAME_LENGTH = 100


class AqiConsts:
    ALERT_THRESHOLD = 300
    AVERAGE_KEY = "average_aqi"
    AVERAGE_DECIMALS = 2
    BEST_CITIES_COUNT = 3
