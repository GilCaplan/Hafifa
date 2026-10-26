import re
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETUP_DIR = PROJECT_ROOT / "setup"


class Settings(BaseSettings):
    """Settings from environment variables or setup/.env (a real environment variable wins)."""

    model_config = SettingsConfigDict(env_file=SETUP_DIR / ".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8010
    reload: bool = False  # accepts true/false, 1/0, yes/no, on/off, in any case
    log_file: Path = Path("air_quality_files/logs/air_quality.log")
    log_level: str = "INFO"
    database_url: str  # required

    @field_validator("log_file")
    @classmethod
    def resolve_from_project_root(cls, path: Path) -> Path:
        """A relative log path is relative to the project root, whichever folder the server is started from."""
        return PROJECT_ROOT / path


settings = Settings()


class App:
    IMPORT_PATH = "air_quality_api.api:app"  # what uvicorn loads


class Log:
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Tables:
    READINGS = "air_quality_readings"
    ALERTS = "alerts"


class Columns:
    # CSV columns (after cleaning: stripped and lowercase)
    DATE = "date"
    CITY = "city"
    PM25 = "pm2.5"
    NO2 = "no2"
    CO2 = "co2"
    # Calculated columns
    AQI = "aqi"
    AQI_LEVEL = "aqi_level"

    POLLUTANTS = [PM25, NO2, CO2]  # in calculate_aqi's argument order  # noqa: RUF012
    REQUIRED = [DATE, CITY, *POLLUTANTS]  # noqa: RUF012
    ALERT = [DATE, CITY, AQI]  # noqa: RUF012
    AQI_HISTORY = [DATE, CITY, AQI, AQI_LEVEL]  # noqa: RUF012


class Validation:
    """Upload validation"""

    CSV_EXTENSION = ".csv"
    DATE_FORMAT = "%Y-%m-%d"
    CSV_HEADER_LINES = 1
    MIN_POLLUTANT_VALUE = 0


class City:
    # Words of letters (any language) joined by single spaces, hyphens or apostrophes, e.g. "Be'er Sheva"
    NAME_REGEX = re.compile(r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$")
    MAX_NAME_LENGTH = 100


class Aqi:
    ALERT_THRESHOLD = 300
    AVERAGE_KEY = "average_aqi"
    AVERAGE_DECIMALS = 2
    BEST_CITIES_COUNT = 3
