import re
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETUP_DIR = PROJECT_ROOT / "setup"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SETUP_DIR / ".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8010
    reload: bool = False  # accepts true/false, 1/0, yes/no, on/off, in any case
    log_file: Path = Path("air_quality_files/logs/air_quality.log")  # relative to PROJECT_ROOT
    log_level: str = "INFO"
    database_url: str  # required


settings = Settings()

# Server
APP_PATH = "air_quality_api.api:app"
HOST = settings.host
PORT = settings.port
RELOAD = settings.reload

# Logging
LOG_FILE = PROJECT_ROOT / settings.log_file
LOG_LEVEL = settings.log_level
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Database
DATABASE_URL = settings.database_url
READINGS_TABLE = "air_quality_readings"
ALERTS_TABLE = "alerts"

# CSV columns (normalized: stripped and lowercase)
DATE_COLUMN = "date"
CITY_COLUMN = "city"
PM25_COLUMN = "pm2.5"
NO2_COLUMN = "no2"
CO2_COLUMN = "co2"
# Calculated columns
AQI_COLUMN = "aqi"
AQI_LEVEL_COLUMN = "aqi_level"

POLLUTANT_COLUMNS = [PM25_COLUMN, NO2_COLUMN, CO2_COLUMN]
REQUIRED_COLUMNS = [DATE_COLUMN, CITY_COLUMN, *POLLUTANT_COLUMNS]
AQI_COLUMNS = [DATE_COLUMN, CITY_COLUMN, AQI_COLUMN]
AQI_LEVEL_COLUMNS = [DATE_COLUMN, CITY_COLUMN, AQI_COLUMN, AQI_LEVEL_COLUMN]


# Upload validation
CSV_EXTENSION = ".csv"
DATE_FORMAT = "%Y-%m-%d"
CSV_HEADER_LINES = 1
MIN_POLLUTANT_VALUE = 0

# Alerts
ALERT_AQI_THRESHOLD = 300

# City names: words of letters (any language) joined by single spaces, hyphens or apostrophes, e.g. "Be'er Sheva"
CITY_NAME_PATTERN = r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$"
CITY_NAME_REGEX = re.compile(CITY_NAME_PATTERN)
MAX_CITY_NAME_LENGTH = 100

# City AQI average and best cities endpoints
AVERAGE_AQI_KEY = "average_aqi"
AVERAGE_AQI_DECIMALS = 2
BEST_CITIES_COUNT = 3
