import re

from app.db.models import Alert, Reading


class ColumnSets:
    POLLUTANTS = [Reading.pm25.key, Reading.no2.key, Reading.co2.key]
    REQUIRED = [Reading.date.key, Reading.city.key, *POLLUTANTS]
    ALERT = [Alert.date.key, Alert.city.key, Alert.aqi.key]


class Consts:
    app_path: str = "app.main:app"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # Postgres allows at most 65,535 values in one statement
    insert_chunk_size: int = 1000


class Validation:
    DATE_FORMAT = "%Y-%m-%d"
    CSV_HEADER_LINES = 1
    MIN_POLLUTANT_VALUE = 0
    # Words of letters (any language) joined by single spaces, hyphens or apostrophes, e.g. "Be'er Sheva"
    CITY_NAME_REGEX = re.compile(r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$")
    MAX_CITY_NAME_LENGTH = 100
