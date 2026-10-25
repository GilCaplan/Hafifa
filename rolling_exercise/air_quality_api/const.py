import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

# Server
APP_PATH = "main:app"
FRONTEND_DIR = PROJECT_ROOT / "air_quality_frontend"
FRONTEND_ROUTE = "/"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8010"))
RELOAD = os.getenv("RELOAD", "false").lower() == "true"

# Logging
LOG_FILE = os.getenv("LOG_FILE", "air_quality.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
# Matches the first line of an entry written with LOG_FORMAT.
# Lines that don't match (like tracebacks) continue the previous entry.
# The request id part is optional so lines written before it was added still parse.
LOG_LINE_PATTERN = (
    r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (?P<logger>\S+) - (?P<level>[A-Z]+) - "
    r"(?:\[(?P<request_id>[^\]]*)\] - )?(?P<message>.*)$"
)
# Every API request gets an id, written on its log lines and sent back in this response header
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_LENGTH = 8
NO_REQUEST_ID = "-"
DEFAULT_LOG_LIMIT = 300
MAX_LOG_LIMIT = 2000
# API routes the request-logging middleware skips (the frontend polls /logs every few seconds)
UNLOGGED_ROUTES = ["/logs"]

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
READINGS_TABLE = "air_quality_readings"
ALERTS_TABLE = "alerts"

# Table browsing (frontend): URL name -> database table and the columns that can be shown and sorted
BROWSABLE_TABLES = {
    "readings": {"table": READINGS_TABLE, "columns": ["id", "date", "city", "pm25", "no2", "co2", "aqi", "aqi_level"]},
    "alerts": {"table": ALERTS_TABLE, "columns": ["id", "date", "city", "aqi"]},
}
DEFAULT_SORT_COLUMN = "date"
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200

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
