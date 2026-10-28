import re
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    app_path: str = "air_quality_api.api:app"  # what uvicorn loads
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("log_file")
    @classmethod
    def resolve_from_project_root(cls, path: Path) -> Path:
        """Keep the logs in the same folder"""
        return PROJECT_ROOT / path


settings = Settings()


class Tables:
    READINGS = "air_quality_readings"
    ALERTS = "alerts"


class Columns:
    # CSV columns
    DATE = "date"
    CITY = "city"
    PM25 = "pm2.5"
    NO2 = "no2"
    CO2 = "co2"
    # Calculated columns
    AQI = "aqi"
    AQI_LEVEL = "aqi_level"

    POLLUTANTS = [PM25, NO2, CO2]  # noqa: RUF012
    REQUIRED = [DATE, CITY, *POLLUTANTS]  # noqa: RUF012
    AQI_HISTORY = [DATE, CITY, AQI, AQI_LEVEL]  # noqa: RUF012
    # The INSERT statements' columns, in order (see air_quality_db/statements.py)
    READING = [DATE, CITY, PM25, NO2, CO2, AQI, AQI_LEVEL]  # noqa: RUF012
    ALERT = [DATE, CITY, AQI]  # noqa: RUF012


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


class Aqi:
    ALERT_THRESHOLD = 300
    AVERAGE_KEY = "average_aqi"
    AVERAGE_DECIMALS = 2
    BEST_CITIES_COUNT = 3
