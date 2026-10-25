from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETUP_DIR = PROJECT_ROOT / "setup"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SETUP_DIR / ".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8010
    reload: bool = False  # accepts true/false, 1/0, yes/no, on/off, in any case
    log_file: Path = Path("air_quality_files/logs/air_quality.log")  # a relative path is relative to PROJECT_ROOT
    log_level: str = "INFO"
    database_url: str  # required: no default


settings = Settings()

# Server
APP_PATH = "main:app"
HOST = settings.host
PORT = settings.port
RELOAD = settings.reload

# Logging
# Resolved from the project root, so it's the same file whichever folder the server is started from
LOG_FILE = PROJECT_ROOT / settings.log_file
LOG_LEVEL = settings.log_level
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
# Every API request gets an id, written on its log lines and sent back in this response header
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_LENGTH = 8
NO_REQUEST_ID = "-"
# API routes the request-logging middleware skips (the frontend polls /logs every few seconds)
UNLOGGED_ROUTES = ["/logs"]

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
POLLUTANT_COLUMNS = [PM25_COLUMN, NO2_COLUMN, CO2_COLUMN]
REQUIRED_COLUMNS = [DATE_COLUMN, CITY_COLUMN, *POLLUTANT_COLUMNS]

# Calculated columns
AQI_COLUMN = "aqi"
AQI_LEVEL_COLUMN = "aqi_level"

# Upload validation
CSV_EXTENSION = ".csv"
DATE_FORMAT = "%Y-%m-%d"
CSV_HEADER_LINES = 1
MIN_POLLUTANT_VALUE = 0

# Alerts
ALERT_AQI_THRESHOLD = 300

# City name validation: letters (any language) in words separated by single spaces, hyphens or apostrophes,
# e.g. "Tel Aviv-Yafo", "Be'er Sheva"
CITY_NAME_PATTERN = r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$"
MAX_CITY_NAME_LENGTH = 100

# City AQI average and best cities endpoints
AVERAGE_AQI_KEY = "average_aqi"
AVERAGE_AQI_DECIMALS = 2
BEST_CITIES_COUNT = 3
