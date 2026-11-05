import re
from datetime import date

from app.db.models import Reading
from app.db.queries import count_rows, get_date_range
from app.support.constants import Validation
from app.support.errors import NotFoundError, ValidationError


def validate_city(city: str) -> str:
    cleaned = re.sub(r"\s+", " ", city).strip()
    if not cleaned:
        raise ValidationError("City name is empty")

    if len(cleaned) > Validation.MAX_CITY_NAME_LENGTH:
        raise ValidationError(f"City name is longer than {Validation.MAX_CITY_NAME_LENGTH} characters")

    if not Validation.CITY_NAME_REGEX.match(cleaned):
        raise ValidationError(f"City name {cleaned!r} can only contain letters, spaces, hyphens and apostrophes")

    if count_rows(Reading, city=cleaned) == 0:
        raise NotFoundError(f"No readings for city {cleaned}. Check the spelling: city names are case-sensitive")

    return cleaned


def validate_dates(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValidationError(f"start_date {start_date} is after end_date {end_date}")

    first, last = get_date_range(Reading)
    if first is None:
        raise NotFoundError("There is no data yet, upload a CSV first")

    if end_date < first or start_date > last:
        raise NotFoundError(f"No data for these dates. The data covers {first} to {last}")
