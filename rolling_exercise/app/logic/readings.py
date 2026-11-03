import logging
from datetime import date

from app.db.models import Reading
from app.db.queries import fetch_rows
from app.logic.validation import validate_city, validate_dates
from app.schemas import ReadingResponse

logger = logging.getLogger(__name__)


def get_air_quality_data(start_date: date, end_date: date) -> list[ReadingResponse]:
    validate_dates(start_date, end_date)
    rows = fetch_rows(Reading, start_date=start_date, end_date=end_date, sort=[Reading.date, Reading.city])
    readings = [ReadingResponse.model_validate(row) for row in rows]

    logger.info(f"Found {len(readings)} readings from {start_date} to {end_date}")
    return readings


def get_air_quality_data_by_city(city: str) -> list[ReadingResponse]:
    city = validate_city(city)
    readings = [ReadingResponse.model_validate(row) for row in fetch_rows(Reading, city=city, sort=Reading.date)]

    logger.info(f"Found {len(readings)} readings for {city}")
    return readings
